"""从模型输出里解析代码块，以及把执行结果格式化回喂给模型。

RLM 的"动作"全部藏在模型输出的 ```repl ... ``` 代码块里。这个模块做两件事：
1. find_code_blocks: 用正则把所有 ```repl 块抠出来（模型一轮可以写多块）。
2. format_repl_output: 把执行结果（stdout/stderr）截断后拼成下一轮的 user 消息。

为什么要截断？因为 stdout 可能打印出几十万字符的 context 切片，如果原样塞回模型
上下文，瞬间就把窗口撑爆了 —— 这恰恰是 RLM 要避免的。所以我们只回喂"够用"的一段。
"""

from __future__ import annotations

import re

from .types import CodeBlock, REPLResult

# 匹配 ```repl\n ... \n``` ，re.DOTALL 让 . 能匹配换行
_CODE_BLOCK_PATTERN = re.compile(r"```repl\s*\n(.*?)```", re.DOTALL)


def find_code_blocks(text: str) -> list[str]:
    """从模型输出里提取所有 ```repl 代码块的内容（按出现顺序）。

    Args:
        text: 模型这一轮的完整文本输出。

    Returns:
        代码字符串列表；没有代码块则返回空列表（这一轮模型只是在"思考"）。
    """
    blocks: list[str] = []
    for match in _CODE_BLOCK_PATTERN.finditer(text):
        code = match.group(1).strip()
        if code:
            blocks.append(code)
    return blocks


def format_repl_output(result: REPLResult, truncate_chars: int = 4000) -> str:
    """把一段代码的执行结果格式化成回喂给模型的文本，超长部分截断。

    Args:
        result: 一段代码的执行结果。
        truncate_chars: stdout/stderr 各自的最大回喂字符数。

    Returns:
        形如 "stdout:\n...\n\nstderr:\n..." 的字符串。
    """
    parts: list[str] = []

    stdout = result.stdout
    if stdout:
        parts.append("stdout:\n" + _truncate(stdout, truncate_chars))
    else:
        parts.append("stdout: (空)")

    if result.stderr:
        parts.append("stderr:\n" + _truncate(result.stderr, truncate_chars))

    return "\n\n".join(parts)


def format_iteration_feedback(
    code_blocks: list[CodeBlock], truncate_chars: int = 4000
) -> str:
    """把一轮里所有代码块的执行结果拼成一条 user 反馈消息。"""
    if not code_blocks:
        return (
            "你这一轮没有写任何 ```repl 代码块。请记住：要和 context 交互、"
            "或提交答案，都必须写 ```repl 代码块。"
        )

    multi = len(code_blocks) > 1
    chunks: list[str] = []
    for i, block in enumerate(code_blocks):
        header = f"REPL 输出（第 {i + 1} 块）：" if multi else "REPL 输出："
        chunks.append(header + "\n" + format_repl_output(block.result, truncate_chars))
    return "\n\n".join(chunks)


def _truncate(text: str, max_chars: int) -> str:
    """超过 max_chars 就截断并标注省略了多少字符。"""
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return text[:max_chars] + f"\n... [已省略 {omitted} 个字符]"


__all__ = ["find_code_blocks", "format_repl_output", "format_iteration_feedback"]
