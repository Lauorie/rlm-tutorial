"""MiniRLM：把"环境 + 提示词 + 循环 + 递归"组装成一个对外像普通 LLM 的东西。

对外接口只有一个：rlm.completion(context, task) -> RLMResult。
内部是 Algorithm 1 的最小实现：

    初始化 REPL，把 context 放进去
    hist = [系统提示 + context 元数据]
    for i in range(max_iterations):
        hist += 第 i 轮提示
        response = LLM(hist)                # 模型决定写什么代码
        code_blocks = 解析 response 里的 ```repl
        for block in code_blocks:
            result = REPL.execute(block)    # 执行，可能触发 llm_query/rlm_query
            if result.final_answer is not None:
                return 它                   # 模型交卷，结束
        hist += (response, REPL 输出反馈)
    return 兜底答案                          # 轮次用尽

递归：completion 给 REPL 注入一个 subcall_fn。当模型在代码里调用 rlm_query(p) 时，
subcall_fn 会新建一个 depth+1 的 MiniRLM 去跑 p —— 除非已经到 max_depth，那就退化成
普通子 LLM 调用（叶子）。这正是论文里的"symbolic recursion"。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .clients import BaseLM, build_client
from .logger import TrajectoryLogger
from .parsing import find_code_blocks, format_iteration_feedback
from .prompts import build_system_messages, build_turn_prompt
from .repl import MiniREPL
from .types import CodeBlock, Message, RLMConfig, RLMIteration, RLMResult

logger = logging.getLogger(__name__)


class MiniRLM:
    """一个递归语言模型。简化但保留核心闭环 + 递归。"""

    def __init__(
        self,
        config: RLMConfig | None = None,
        client: BaseLM | None = None,
        custom_tools: dict[str, Any] | None = None,
        trajectory_logger: TrajectoryLogger | None = None,
        depth: int = 0,
        **client_kwargs: Any,
    ) -> None:
        """
        Args:
            config: RLM 配置；不传则用默认值。
            client: 直接传入的 LLM 客户端（测试时常用 MockLM）；不传则按 config.backend 造。
            custom_tools: 注入 REPL 的自定义工具。
            trajectory_logger: 轨迹日志记录器；None 时只在内存里保存。
            depth: 当前递归深度（递归时由父 RLM 设置）。
            **client_kwargs: 传给 build_client（如 api_key/base_url/responses）。
        """
        self.config = config or RLMConfig()
        self.depth = depth
        self.custom_tools = custom_tools or {}
        self.trajectory_logger = trajectory_logger
        self._client = client or build_client(
            self.config.backend, self.config.model_name, **client_kwargs
        )
        self._client_kwargs = client_kwargs

    # ---- 对外主入口 -----------------------------------------------------

    def completion(self, context: Any, task: str | None = None) -> RLMResult:
        """对一段（可能超长的）context 运行 RLM，返回最终结果。

        Args:
            context: 超长输入，会被卸载进 REPL 的 `context` 变量。
            task: 可选的任务描述。

        Returns:
            RLMResult，含最终回答、完整迭代轨迹、token 统计。
        """
        start = time.perf_counter()
        repl = self._make_repl()
        repl.load_context(context)

        context_type = type(context).__name__
        context_length = len(context) if hasattr(context, "__len__") else 0
        history: list[Message] = build_system_messages(
            context_length=context_length,
            context_type=context_type,
            task=task,
        )

        result = RLMResult(response="", root_model=self.config.model_name, depth=self.depth)

        for i in range(self.config.max_iterations):
            history.append(build_turn_prompt(i, self.config.max_iterations))
            iteration = self._run_one_turn(i, history, repl)
            result.iterations.append(iteration)

            if iteration.final_answer is not None:
                result.response = iteration.final_answer
                result.stopped_reason = "final_answer"
                break

            # 把"模型这一轮说了什么 + REPL 反馈"接回历史，进入下一轮
            history.append(Message(role="assistant", content=iteration.response))
            history.append(
                Message(
                    role="user",
                    content=format_iteration_feedback(
                        iteration.code_blocks, self.config.stdout_truncate_chars
                    ),
                )
            )
        else:
            # 轮次用尽还没交卷：兜底取最后一次非空响应
            result.response = self._fallback_answer(result)
            result.stopped_reason = "max_iterations"

        result.usage.merge(repl.usage)
        result.execution_time = time.perf_counter() - start

        if self.trajectory_logger is not None and self.depth == 0:
            self.trajectory_logger.write(result, self.config)

        return result

    # ---- 一轮迭代 -------------------------------------------------------

    def _run_one_turn(
        self, i: int, history: list[Message], repl: MiniREPL
    ) -> RLMIteration:
        """跑一轮：调模型 → 解析代码 → 逐块执行 → 收集结果。"""
        turn_start = time.perf_counter()
        response, in_tok, out_tok = self._client.completion(history)
        repl.usage.add(in_tok, out_tok)

        code_blocks: list[CodeBlock] = []
        final_answer: str | None = None
        for code in find_code_blocks(response):
            repl_result = repl.execute_code(code)
            code_blocks.append(CodeBlock(code=code, result=repl_result))
            if repl_result.final_answer is not None:
                final_answer = repl_result.final_answer
                break  # 交卷了，本轮剩余代码块不再执行

        return RLMIteration(
            iteration=i,
            prompt=list(history),  # 快照，方便前端回看当时的完整上下文
            response=response,
            code_blocks=code_blocks,
            final_answer=final_answer,
            iteration_time=time.perf_counter() - turn_start,
        )

    # ---- 递归 -----------------------------------------------------------

    def _make_repl(self) -> MiniREPL:
        """造一个 REPL，并按深度决定是否给它递归能力。"""
        subcall_fn = None
        if self.depth + 1 < self.config.max_depth:
            subcall_fn = self._spawn_subcall
        return MiniREPL(
            client=self._client,
            subcall_fn=subcall_fn,
            custom_tools=self.custom_tools,
            depth=self.depth,
        )

    def _spawn_subcall(self, prompt: str) -> RLMResult:
        """rlm_query 的实现：新建一个 depth+1 的 MiniRLM 来处理 prompt。"""
        child = MiniRLM(
            config=self.config,
            client=self._client,
            custom_tools=self.custom_tools,
            trajectory_logger=None,  # 子调用轨迹已嵌在父结果里，不单独落盘
            depth=self.depth + 1,
            **self._client_kwargs,
        )
        # 子调用把 prompt 同时当作 context 和 task —— 它要对这段内容做完整 RLM 处理
        return child.completion(context=prompt, task=prompt)

    # ---- 兜底 -----------------------------------------------------------

    @staticmethod
    def _fallback_answer(result: RLMResult) -> str:
        for it in reversed(result.iterations):
            if it.response.strip():
                return it.response.strip()
        return "(未能在限定轮次内得到答案)"


__all__ = ["MiniRLM"]
