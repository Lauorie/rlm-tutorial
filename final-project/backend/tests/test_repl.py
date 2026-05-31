"""MiniREPL 单元测试：持久化、stdout 捕获、答案捕获、报错恢复。

这些测试完全不需要 API key —— REPL 本身就是纯本地的。
"""

from mini_rlm import MiniREPL, MockLM


def make_repl() -> MiniREPL:
    return MiniREPL(client=MockLM(responses=["unused"]))


def test_variable_persists_across_calls() -> None:
    """变量应跨多次 execute_code 保留 —— 这是 REPL 的本质。"""
    repl = make_repl()
    repl.execute_code("x = 1 + 2")
    result = repl.execute_code("y = x * 10\nprint(y)")
    assert "30" in result.stdout
    assert repl.ns["y"] == 30


def test_stdout_is_captured() -> None:
    repl = make_repl()
    result = repl.execute_code("print('hello RLM')")
    assert "hello RLM" in result.stdout
    assert result.stderr == ""


def test_error_is_captured_not_raised() -> None:
    """模型代码报错时不应让整个程序崩溃，而是把 traceback 喂回去。"""
    repl = make_repl()
    result = repl.execute_code("1 / 0")
    assert "ZeroDivisionError" in result.stderr
    # 报错后 REPL 仍可继续用
    result2 = repl.execute_code("print('still alive')")
    assert "still alive" in result2.stdout


def test_context_is_accessible() -> None:
    repl = make_repl()
    repl.load_context("a" * 500)
    result = repl.execute_code("print(len(context))")
    assert "500" in result.stdout


def test_answer_capture() -> None:
    """设置 answer['ready']=True 应触发 final_answer 捕获。"""
    repl = make_repl()
    result = repl.execute_code(
        "answer['content'] = '42'\nanswer['ready'] = True"
    )
    assert result.final_answer == "42"


def test_llm_query_injected() -> None:
    """REPL 里应能调用 llm_query。"""
    repl = MiniREPL(client=MockLM(responses=["四"]))
    result = repl.execute_code("r = llm_query('二加二等于几')\nprint(r)")
    assert "四" in result.stdout
    assert len(result.rlm_calls) == 1


def test_custom_tools() -> None:
    def double(x: int) -> int:
        return x * 2

    repl = MiniREPL(client=MockLM(responses=["x"]), custom_tools={"double": double})
    result = repl.execute_code("print(double(21))")
    assert "42" in result.stdout
