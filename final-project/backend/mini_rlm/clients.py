"""LLM 客户端：统一接口 + 两个实现（OpenAI 兼容 / Mock）。

教学版只做两个 provider：
- OpenAICompatClient：调用任何 OpenAI 兼容的 /chat/completions 接口（OpenAI 官方、
  国内代理、本地 vLLM 都行），靠 base_url 切换。
- MockLM：不联网、零成本，用预设脚本或一个函数生成回复，让读者无需 API key 就能跑通
  整个 RLM 循环和可视化。

两者都实现 BaseLM.completion(messages) -> (text, input_tokens, output_tokens)，
上层 RLM 完全不关心底下是真模型还是假模型。
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from .types import Message

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """没有 tokenizer 时的粗略估算：约 4 字符 = 1 token。"""
    return max(1, len(text) // 4)


class BaseLM(ABC):
    """所有 LLM 客户端的统一接口。"""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @abstractmethod
    def completion(self, messages: list[Message]) -> tuple[str, int, int]:
        """同步补全。

        Args:
            messages: OpenAI 风格消息列表。

        Returns:
            (生成文本, 输入 token 数, 输出 token 数)
        """
        raise NotImplementedError


class OpenAICompatClient(BaseLM):
    """调用 OpenAI 兼容接口的客户端。"""

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
        **sampling_args: Any,
    ) -> None:
        super().__init__(model_name)
        # 延迟导入，保证没装 openai 也能用 MockLM
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "使用真实模型需要先安装 openai：pip install openai"
            ) from exc

        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            timeout=timeout,
        )
        self.sampling_args = sampling_args

    def completion(self, messages: list[Message]) -> tuple[str, int, int]:
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=[m.to_dict() for m in messages],
                **self.sampling_args,
            )
        except Exception:
            logger.exception("OpenAI 兼容接口调用失败")
            raise

        text = resp.choices[0].message.content or ""
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else _estimate_tokens(str(messages))
        out_tok = usage.completion_tokens if usage else _estimate_tokens(text)
        return text, in_tok, out_tok


class MockLM(BaseLM):
    """零成本的假模型，三种用法：

    1. 脚本模式：responses=[...]，按顺序吐出（最常用于教学，行为完全确定）。
    2. 函数模式：response_fn=lambda messages: "...", 根据输入动态生成。
    3. 默认模式：直接回显最后一条消息，方便快速冒烟。
    """

    def __init__(
        self,
        model_name: str = "mock-model",
        responses: list[str] | None = None,
        response_fn: Callable[[list[Message]], str] | None = None,
    ) -> None:
        super().__init__(model_name)
        self._responses = list(responses) if responses is not None else None
        self._response_fn = response_fn
        self._idx = 0

    def completion(self, messages: list[Message]) -> tuple[str, int, int]:
        if self._responses is not None:
            if self._idx >= len(self._responses):
                # 脚本用完了还在被调用：兜底提交一个空答案，避免死循环
                text = (
                    "```repl\n"
                    "answer['content'] = answer.get('content') or '(mock 脚本已用尽)'\n"
                    "answer['ready'] = True\n"
                    "```"
                )
            else:
                text = self._responses[self._idx]
                self._idx += 1
        elif self._response_fn is not None:
            text = self._response_fn(messages)
        else:
            last = messages[-1].content if messages else ""
            text = f"Mock 回复（回显）：{last[:80]}"

        in_tok = _estimate_tokens("".join(m.content for m in messages))
        return text, in_tok, _estimate_tokens(text)


def build_client(
    backend: str,
    model_name: str,
    **kwargs: Any,
) -> BaseLM:
    """根据 backend 名字造一个客户端。

    Args:
        backend: "mock" | "openai"
        model_name: 模型名。
        **kwargs: 透传给具体客户端（如 mock 的 responses / openai 的 api_key）。
    """
    if backend == "mock":
        return MockLM(
            model_name=model_name,
            responses=kwargs.get("responses"),
            response_fn=kwargs.get("response_fn"),
        )
    if backend == "openai":
        return OpenAICompatClient(
            model_name=model_name,
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            **{
                k: v
                for k, v in kwargs.items()
                if k not in {"api_key", "base_url", "responses", "response_fn"}
            },
        )
    raise ValueError(f"未知 backend: {backend!r}，仅支持 'mock' / 'openai'")


__all__ = ["BaseLM", "OpenAICompatClient", "MockLM", "build_client"]
