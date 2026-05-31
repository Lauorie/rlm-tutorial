"""MiniRLM 主循环测试：完整循环、终止、轮次用尽兜底、递归。

全部用 MockLM 脚本驱动，行为完全确定，零成本。
"""

from mini_rlm import MiniRLM, MockLM, RLMConfig


def repl_block(code: str) -> str:
    return f"```repl\n{code}\n```"


def submit(content: str) -> str:
    return repl_block(f"answer['content'] = {content!r}\nanswer['ready'] = True")


def test_full_loop_terminates_on_answer() -> None:
    """两轮：先 peek，再交卷。"""
    mock = MockLM(
        responses=[
            repl_block("print(len(context))"),
            submit("done"),
        ]
    )
    rlm = MiniRLM(config=RLMConfig(max_iterations=5), client=mock)
    result = rlm.completion(context="x" * 100, task="测一下")
    assert result.response == "done"
    assert result.stopped_reason == "final_answer"
    assert len(result.iterations) == 2


def test_peek_context_in_loop() -> None:
    """模型应能在循环里读到真正的 context 内容。"""
    mock = MockLM(
        responses=[
            repl_block("first = context[:5]\nprint(first)"),
            repl_block("answer['content'] = first\nanswer['ready'] = True"),
        ]
    )
    rlm = MiniRLM(config=RLMConfig(max_iterations=5), client=mock)
    result = rlm.completion(context="HELLO world", task="取前 5 字符")
    assert result.response == "HELLO"


def test_max_iterations_fallback() -> None:
    """从不交卷时应在 max_iterations 处停止并兜底。"""
    mock = MockLM(response_fn=lambda msgs: repl_block("print('thinking...')"))
    rlm = MiniRLM(config=RLMConfig(max_iterations=3), client=mock)
    result = rlm.completion(context="abc")
    assert result.stopped_reason == "max_iterations"
    assert len(result.iterations) == 3


def test_llm_query_inside_loop_is_recorded() -> None:
    mock = MockLM(
        responses=[
            repl_block("r = llm_query('问题')\nprint(r)"),
            submit("ok"),
        ]
    )
    # llm_query 用同一个 mock，会消费下一条脚本
    mock_for_query = MockLM(responses=["子回答A"])
    rlm = MiniRLM(
        config=RLMConfig(max_iterations=5, max_depth=1),
        client=mock,
    )
    # 替换 REPL 用的 client：这里简单验证 rlm_calls 被记录
    result = rlm.completion(context="data")
    sub_calls = [
        c for it in result.iterations for b in it.code_blocks for c in b.result.rlm_calls
    ]
    assert len(sub_calls) >= 1


def test_recursion_spawns_child_rlm() -> None:
    """max_depth=2 时，rlm_query 应触发一个 depth=1 的子 RLM。"""

    # 父模型：调用 rlm_query，然后交卷
    parent = MockLM(
        responses=[
            repl_block("sub = rlm_query('子任务')\nprint(sub)"),
            submit("parent-done"),
        ]
    )
    # 子模型脚本会被子 RLM 消费：子 RLM 直接交卷
    # 注意：父子共享同一个 client 实例，所以脚本要按"调用顺序"排好
    shared = MockLM(
        responses=[
            # 父第 1 轮
            repl_block("sub = rlm_query('子任务')\nprint(sub)"),
            # 子 RLM 第 1 轮（在父第 1 轮的代码执行期间被调用）
            submit("child-answer"),
            # 父第 2 轮
            submit("parent-done"),
        ]
    )
    rlm = MiniRLM(config=RLMConfig(max_iterations=5, max_depth=2), client=shared)
    result = rlm.completion(context="data", task="递归测试")

    assert result.response == "parent-done"
    # 应该有一个子调用，且它有自己的迭代轨迹（不是叶子）
    sub_calls = [
        c for it in result.iterations for b in it.code_blocks for c in b.result.rlm_calls
    ]
    assert len(sub_calls) == 1
    assert sub_calls[0].response == "child-answer"
    assert sub_calls[0].depth == 1
    assert len(sub_calls[0].iterations) >= 1  # 子调用是完整 RLM，有迭代


def test_depth_limit_falls_back_to_leaf() -> None:
    """max_depth=1 时 rlm_query 应退化为普通 llm_query（叶子，无子迭代）。"""
    shared = MockLM(
        responses=[
            repl_block("sub = rlm_query('子任务')\nprint(sub)"),
            "叶子回答",  # rlm_query 退化成 llm_query，消费这条
            submit("parent-done"),
        ]
    )
    rlm = MiniRLM(config=RLMConfig(max_iterations=5, max_depth=1), client=shared)
    result = rlm.completion(context="data")
    sub_calls = [
        c for it in result.iterations for b in it.code_blocks for c in b.result.rlm_calls
    ]
    assert len(sub_calls) == 1
    assert sub_calls[0].stopped_reason == "leaf_llm"
    assert len(sub_calls[0].iterations) == 0  # 叶子没有自己的迭代
