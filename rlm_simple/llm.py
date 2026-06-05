import os
import logging
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI, APIError

# 加载环境变量（确保在初始化客户端前执行）
load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-5.4-mini"  # 自动检测失败时的回退模型


class LLMClient:
    """基于 OpenAI SDK 的轻量级 LLM 客户端。"""

    def __init__(
        self,
        model: str = "auto",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> None:
        """初始化客户端。

        Args:
            model: 模型名；传入 "auto" 时自动探测可用模型。
            max_tokens: 单次回复的最大 token 数。
            temperature: 采样温度。

        Raises:
            ValueError: 未找到 API Key 时抛出。
        """
        # 优先从环境变量读取配置，兼容 .env 文件
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("RLM_API_URL")

        if not api_key:
            raise ValueError("未找到 API Key，请设置 OPENAI_API_KEY 或 API_KEY 环境变量")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.model = self._resolve_model(model)

    def _resolve_model(self, model: str) -> str:
        """自动检测可用模型，失败时回退到默认值。"""
        if model != "auto":
            return model
        try:
            models = self.client.models.list()
            # 兼容不同 API 返回格式（data 列表或直接列表）
            model_list = models.data if hasattr(models, "data") else models
            if model_list:
                first_model = model_list[0]
                resolved = first_model.id if hasattr(first_model, "id") else str(first_model)
                logger.info("自动选择模型: %s", resolved)
                return resolved
        except APIError as e:
            logger.warning("模型自动检测失败: %s", e)
        except Exception as e:  # noqa: BLE001 — 探测失败不应阻断启动
            logger.warning("模型自动检测异常: %s", e)
        return DEFAULT_MODEL

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> str:
        """发送对话请求并返回助手回复内容。

        Args:
            messages: OpenAI 格式的消息列表。
            max_tokens: 覆盖默认的最大 token 数。
            temperature: 覆盖默认采样温度。

        Returns:
            助手回复的纯文本内容。

        Raises:
            RuntimeError: API 调用失败时抛出。
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
                **kwargs,
            )
            content = response.choices[0].message.content
            return content or ""
        except APIError as e:
            logger.error("LLM 请求失败: %s", e)
            raise RuntimeError(f"LLM 请求失败: {e}") from e
