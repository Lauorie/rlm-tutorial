"""mini-RLM 的核心数据类型。

这里把"一次 RLM 运行"拆成几层嵌套的数据结构，刻意和官方可视化器的 JSONL
轨迹格式保持一致，这样前端可以直接复用：

    RLMResult                 # 一次 completion 的最终结果
    └── iterations: list[RLMIteration]
            └── code_blocks: list[CodeBlock]
                    └── result: REPLResult
                            └── rlm_calls: list[RLMResult]   # 递归子调用（嵌套！）

注意 REPLResult.rlm_calls 里装的又是 RLMResult —— 这正是"递归"在数据结构上的体现。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RLMConfig:
    """RLM 实例的不可变配置。

    用 frozen=True 保证配置在一次运行里不会被偷偷改掉，方便复现实验。
    """

    model_name: str = "mock-model"
    max_iterations: int = 12
    max_depth: int = 2
    stdout_truncate_chars: int = 4000
    backend: str = "mock"


@dataclass
class Message:
    """一条对话消息，OpenAI 风格。role ∈ {system, user, assistant}。"""

    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class UsageSummary:
    """token / 成本统计。教学版只统计 token，成本留作练习。"""

    total_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.total_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def merge(self, other: "UsageSummary") -> None:
        self.total_calls += other.total_calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens

    def to_dict(self) -> dict[str, int]:
        return {
            "total_calls": self.total_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


@dataclass
class REPLResult:
    """一段代码在 REPL 里执行后的结果。"""

    stdout: str = ""
    stderr: str = ""
    locals: dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    # 本段代码里发生的递归子调用（rlm_query / llm_query 触发的）
    rlm_calls: list["RLMResult"] = field(default_factory=list)
    # 若代码里设置了 answer["ready"] = True，这里会被填上最终答案
    final_answer: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            # locals 里可能有不可序列化的对象，统一转成字符串预览，避免日志写挂
            "locals": {k: _safe_preview(v) for k, v in self.locals.items()},
            "execution_time": self.execution_time,
            "rlm_calls": [c.to_dict() for c in self.rlm_calls],
            "final_answer": self.final_answer,
        }


@dataclass
class CodeBlock:
    """模型在某一轮生成的一段 ```repl``` 代码及其执行结果。"""

    code: str
    result: REPLResult

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "result": self.result.to_dict()}


@dataclass
class RLMIteration:
    """RLM 主循环的一轮迭代记录。"""

    iteration: int
    prompt: list[Message]
    response: str
    code_blocks: list[CodeBlock] = field(default_factory=list)
    final_answer: str | None = None
    iteration_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "prompt": [m.to_dict() for m in self.prompt],
            "response": self.response,
            "code_blocks": [b.to_dict() for b in self.code_blocks],
            "final_answer": self.final_answer,
            "iteration_time": self.iteration_time,
        }


@dataclass
class RLMResult:
    """一次 rlm.completion() 的最终结果，也是递归子调用的返回类型。"""

    response: str
    root_model: str
    depth: int = 0
    iterations: list[RLMIteration] = field(default_factory=list)
    usage: UsageSummary = field(default_factory=UsageSummary)
    execution_time: float = 0.0
    stopped_reason: str = "final_answer"  # final_answer | max_iterations | error

    def to_dict(self) -> dict[str, Any]:
        return {
            "response": self.response,
            "root_model": self.root_model,
            "depth": self.depth,
            "iterations": [it.to_dict() for it in self.iterations],
            "usage": self.usage.to_dict(),
            "execution_time": self.execution_time,
            "stopped_reason": self.stopped_reason,
        }


def _safe_preview(value: Any, max_len: int = 200) -> str:
    """把任意变量转成短字符串预览，保证日志可 JSON 序列化。"""
    try:
        text = repr(value)
    except Exception:  # 极少数对象的 repr 也会抛错
        text = f"<{type(value).__name__}>"
    if len(text) > max_len:
        return text[:max_len] + f"... (+{len(text) - max_len} chars)"
    return text


__all__ = [
    "RLMConfig",
    "Message",
    "UsageSummary",
    "REPLResult",
    "CodeBlock",
    "RLMIteration",
    "RLMResult",
]
