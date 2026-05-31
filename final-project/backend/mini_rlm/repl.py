"""MiniREPL：一个能记住变量、能捕获 stdout、能调用 LLM 的持久化 Python 执行环境。

这是 RLM 思想里"环境 E"的最小实现。三个关键点：

1. 持久化：所有代码都在同一个命名空间字典 self.ns 里 exec，所以这一轮建的变量
   下一轮还在 —— 这是 REPL 而不是一次性 eval 的本质。
2. context 卸载：超长输入作为 self.ns["context"] 存在，模型只能通过写代码去 peek，
   永远不会自动进入模型上下文窗口。
3. 工具注入：llm_query / rlm_query / answer 作为命名空间里的对象注入，模型在代码里
   直接调用它们 —— 这就是"符号化地调用语言模型"。

⚠️ 安全提示：教学版用 exec 直接在本进程执行模型生成的代码，这 **不是** 安全沙箱。
官方项目用 Docker/E2B/Modal 等隔离环境来跑不可信代码。生产环境务必隔离。
"""

from __future__ import annotations

import io
import time
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from .clients import BaseLM
from .types import Message, REPLResult, RLMResult, UsageSummary


class _AnswerDict(dict):
    """特制的 answer 字典：当代码里设置 answer["ready"] = True 时触发回调。

    这样 RLM 主循环就能知道"模型交卷了"，而不需要轮询。
    """

    def __init__(self, on_ready: Callable[[str], None]) -> None:
        super().__init__()
        super().__setitem__("content", "")
        super().__setitem__("ready", False)
        self._on_ready = on_ready

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        if key == "ready" and value:
            self._on_ready(str(self.get("content", "")))


class MiniREPL:
    """RLM 的执行环境。一次 RLM 运行对应一个 MiniREPL 实例。"""

    def __init__(
        self,
        client: BaseLM,
        subcall_fn: Callable[[str], RLMResult] | None = None,
        custom_tools: dict[str, Any] | None = None,
        depth: int = 0,
    ) -> None:
        """
        Args:
            client: 供 llm_query 使用的底层 LLM 客户端。
            subcall_fn: 供 rlm_query 使用的递归回调；None 时 rlm_query 退化为 llm_query。
            custom_tools: 额外注入命名空间的函数/数据。
            depth: 当前递归深度（仅用于日志标注）。
        """
        self._client = client
        self._subcall_fn = subcall_fn
        self._depth = depth
        self._custom_tools = custom_tools or {}

        self.usage = UsageSummary()
        self._final_answer: str | None = None
        self._pending_calls: list[RLMResult] = []

        self.ns: dict[str, Any] = {}
        self._setup_namespace()

    # ---- 初始化命名空间 -------------------------------------------------

    def _setup_namespace(self) -> None:
        """把工具函数、answer、自定义工具注入命名空间。"""
        self.ns["__builtins__"] = __builtins__
        self.ns["llm_query"] = self._llm_query
        self.ns["llm_query_batched"] = self._llm_query_batched
        self.ns["rlm_query"] = self._rlm_query
        self.ns["answer"] = _AnswerDict(on_ready=self._capture_answer)
        for name, value in self._custom_tools.items():
            self.ns[name] = value

    def _capture_answer(self, content: str) -> None:
        self._final_answer = content

    # ---- 加载 context ---------------------------------------------------

    def load_context(self, context: Any) -> None:
        """把超长输入放进 REPL，作为 `context` 变量。模型只能写代码去看它。"""
        self.ns["context"] = context

    # ---- 注入的工具：llm_query / rlm_query ------------------------------

    def _llm_query(self, prompt: str) -> str:
        """单次子 LLM 调用：开一个全新的、无 REPL、无记忆的模型回答 prompt。"""
        text, in_tok, out_tok = self._client.completion(
            [Message(role="user", content=prompt)]
        )
        self.usage.add(in_tok, out_tok)
        # 记成一个"叶子"子调用，供前端展示
        self._pending_calls.append(
            RLMResult(
                response=text,
                root_model=self._client.model_name,
                depth=self._depth + 1,
                usage=UsageSummary(total_calls=1, input_tokens=in_tok, output_tokens=out_tok),
                stopped_reason="leaf_llm",
            )
        )
        return text

    def _llm_query_batched(self, prompts: list[str]) -> list[str]:
        """批量单次调用。教学版用串行实现，并发留作练习。"""
        return [self._llm_query(p) for p in prompts]

    def _rlm_query(self, prompt: str) -> str:
        """递归子调用：当深度允许时，子调用本身又是一个完整 RLM（有自己的 REPL）。"""
        if self._subcall_fn is None:
            # 没有递归能力（已到最大深度），退化为普通子 LLM 调用
            return self._llm_query(prompt)
        result = self._subcall_fn(prompt)
        self.usage.merge(result.usage)
        self._pending_calls.append(result)
        return result.response

    # ---- 执行代码 -------------------------------------------------------

    def execute_code(self, code: str) -> REPLResult:
        """在持久化命名空间里执行一段代码，捕获 stdout/stderr 和最终答案。"""
        self._pending_calls = []
        stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
        start = time.perf_counter()

        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(code, self.ns, self.ns)  # noqa: S102 教学用途，非安全沙箱
            stderr = stderr_buf.getvalue()
        except Exception as exc:  # 捕获模型代码里的任何报错，喂回去让它自我修正
            import traceback

            stderr = stderr_buf.getvalue() + traceback.format_exc()
            # 不 re-raise：RLM 的精髓之一是模型能从执行报错中恢复
            _ = exc

        return REPLResult(
            stdout=stdout_buf.getvalue(),
            stderr=stderr,
            locals={
                k: v
                for k, v in self.ns.items()
                if not k.startswith("_") and not callable(v) and k != "answer"
            },
            execution_time=time.perf_counter() - start,
            rlm_calls=list(self._pending_calls),
            final_answer=self._final_answer,
        )


__all__ = ["MiniREPL"]
