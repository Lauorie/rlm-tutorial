"""代码块解析与截断测试。"""

from mini_rlm.parsing import find_code_blocks, format_repl_output, _truncate
from mini_rlm.types import REPLResult


def test_find_single_block() -> None:
    text = "我先看看\n```repl\nprint(len(context))\n```\n看完再说"
    blocks = find_code_blocks(text)
    assert blocks == ["print(len(context))"]


def test_find_multiple_blocks() -> None:
    text = "```repl\na = 1\n```\n中间说点话\n```repl\nb = 2\n```"
    blocks = find_code_blocks(text)
    assert blocks == ["a = 1", "b = 2"]


def test_no_block_returns_empty() -> None:
    assert find_code_blocks("纯思考，没有代码") == []


def test_ignores_non_repl_fences() -> None:
    """普通 ```python 块不应被当作 repl 动作。"""
    text = "```python\nprint('hi')\n```"
    assert find_code_blocks(text) == []


def test_truncate() -> None:
    out = _truncate("a" * 100, 10)
    assert out.startswith("a" * 10)
    assert "已省略 90" in out


def test_format_repl_output_truncates() -> None:
    result = REPLResult(stdout="x" * 5000)
    formatted = format_repl_output(result, truncate_chars=100)
    assert "已省略" in formatted
