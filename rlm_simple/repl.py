import io
import ast
import types
import asyncio
import inspect
import logging
import contextlib
import traceback
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class _Final(Exception):
    """内部信号：REPL 代码调用 FINAL() 时抛出，用于结束迭代并携带答案。"""

    def __init__(self, value: Any) -> None:
        self.value = value
        super().__init__("FINAL called")


class REPLEnv:
    """供主 LLM 执行代码的异步 Python REPL 沙箱（类 Jupyter，状态跨次保留）。

    暴露给执行代码的变量：
      - ``context``    : 待处理的长文本 / 任意上下文对象
      - ``llm_query``  : **异步**函数，递归调用子 LLM，需 ``await llm_query(...)``
      - ``FINAL``      : 函数，调用 ``FINAL(value)`` 提交最终答案（value 可为任意原生类型）
      - ``print``      : 标准输出会被捕获并回灌给主 LLM

    代码支持顶层 ``await`` 与 ``asyncio.gather``，变量在多次 execute 间持久化。
    """

    def __init__(
        self,
        llm_query_fn: Callable[[str], Awaitable[Any]],
        context: Any,
    ) -> None:
        # 单一命名空间同时作为 globals 与 locals，配合 module 级字节码实现
        # 跨执行的变量持久化（贴近 Jupyter / asyncio REPL 语义）。
        self.namespace: dict = {
            "__builtins__": __builtins__,
            "context": context,
            "llm_query": llm_query_fn,
            "FINAL": self._final,
        }
        self.has_final: bool = False
        self.final_value: Any = None
        # 独立事件循环，用于驱动代码中的顶层 await / asyncio.gather
        self._loop = asyncio.new_event_loop()

    def _final(self, value: Any) -> None:
        """REPL 内 FINAL() 的实现：记录答案并中断本次执行。"""
        self.has_final = True
        self.final_value = value
        raise _Final(value)

    def close(self) -> None:
        """关闭内部事件循环。"""
        if not self._loop.is_closed():
            self._loop.close()

    def execute(self, code: str) -> str:
        """执行 Python 代码（支持顶层 await）并捕获 stdout。

        Args:
            code: 待执行的 Python 源码。

        Returns:
            捕获到的标准输出；FINAL() 时返回提示；异常时附加 traceback。
        """
        buffer = io.StringIO()
        try:
            compiled = compile(
                code, "<repl>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
            )
            func = types.FunctionType(compiled, self.namespace)
            with contextlib.redirect_stdout(buffer):
                result = func()
                if inspect.iscoroutine(result):
                    self._loop.run_until_complete(result)
        except _Final:
            # 主 LLM 调用了 FINAL()，视为正常结束。
            output = buffer.getvalue()
            return f"{output}\n(final answer submitted)" if output else "(final answer submitted)"
        except Exception:  # noqa: BLE001 — 任何执行错误都回灌给 LLM 自行修正
            output = buffer.getvalue()
            tb = traceback.format_exc()
            logger.debug("REPL 执行异常:\n%s", tb)
            return f"{output}{tb}" if output else tb

        output = buffer.getvalue()
        return output if output else "(no output)"
