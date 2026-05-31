"""系统提示词：把一个普通 LLM "调教"成 RLM 的关键。

RLM 不改模型权重，全靠 prompt 告诉模型三件事：
1. 你的超长 context 已经放在 REPL 的 `context` 变量里了，别指望我直接喂给你；
2. 你可以写 ```repl 代码块去 peek/切分/处理它，还能在代码里调用 llm_query / rlm_query；
3. 想交答案，就在代码里设置 answer["content"] 和 answer["ready"] = True。

这就是"符号化操作 prompt"思想的提示词落地。官方提示词更长（含编排策略、in-context
示例等），这里保留最小可用骨架，方便教学。
"""

from __future__ import annotations

import textwrap

from .types import Message

SYSTEM_PROMPT = textwrap.dedent(
    """\
    You are a Recursive Language Model (RLM). Your task's long context does NOT
    sit in your chat window. Instead it lives as a variable `context` inside a
    persistent Python REPL that you control by writing code.

    To act, write a ```repl code block. The REPL persists across turns, so any
    variable you create stays available next turn. You will be queried turn by
    turn until you submit a final answer.

    Available inside the REPL:
    - `context`: the (possibly huge) input, usually a `str` or `list[str]`.
      Peek at it with slicing/len/regex BEFORE doing anything else.
    - `llm_query(prompt: str) -> str`: ask a fresh sub-LLM a question. It has no
      REPL and no memory; it only sees the prompt string you pass. Use it to
      process a *slice* of the context.
    - `rlm_query(prompt: str) -> str`: like llm_query, but the sub-call is itself
      a full RLM (with its own REPL) when recursion depth allows. Use it for
      sub-tasks that are themselves long/complex.
    - `answer`: a dict initialised to {{"content": "", "ready": False}}.
      To submit, set answer["content"] = <your final answer> and
      answer["ready"] = True inside a ```repl block.
    - `print(...)`: stdout is captured and shown back to you (truncated if long).

    Rules:
    - First, inspect `context` (length, a short prefix). Do NOT answer blindly.
    - Keep YOUR window small. Never print the whole context. Push heavy reading
      into llm_query/rlm_query calls over slices.
    - Build intermediate results into variables; stitch them together in code.
    - When confident, set answer["ready"] = True. That ends the loop.
    {custom_tools_section}
    """
)


def build_system_messages(
    context_length: int,
    context_type: str,
    task: str | None,
    custom_tools_desc: str = "",
) -> list[Message]:
    """构造对话开头的 system + user 两条消息。

    Args:
        context_length: context 的总字符数（让模型对规模有概念）。
        context_type: "str" / "list" / "dict"，告诉模型怎么切。
        task: 可选的任务描述（root prompt）。
        custom_tools_desc: 自定义工具说明，拼进系统提示。

    Returns:
        [system_message, user_message]
    """
    custom_section = ""
    if custom_tools_desc:
        custom_section = "\n额外可用的自定义工具：\n" + custom_tools_desc

    system_content = SYSTEM_PROMPT.format(custom_tools_section=custom_section)

    body = (
        f"你的 context 是一个 {context_type}，共约 {context_length} 个字符。"
        "每次 llm_query 大约能吃下 ~10 万字符。先 peek 再动手。"
    )
    if task:
        body = f"请完成下面的任务：\n{task}\n\n{body}"

    return [
        Message(role="system", content=system_content),
        Message(role="user", content=body),
    ]


def build_turn_prompt(iteration: int, max_iterations: int) -> Message:
    """每一轮追加的 user 提示，标注轮次；第 0 轮额外提醒先探查。"""
    head = f"第 {iteration + 1}/{max_iterations} 轮："
    if iteration == 0:
        head = (
            "你还没有查看过 context。请先写一个 ```repl 代码块查看它的长度和开头，"
            "不要急着给最终答案。\n\n" + head
        )
    return Message(role="user", content=head)


__all__ = ["SYSTEM_PROMPT", "build_system_messages", "build_turn_prompt"]
