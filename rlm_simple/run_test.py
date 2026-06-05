"""长文本阅读理解演示。

以论文 Recursive_Language_Models.md（约 159KB）为上下文，依次跑几个
针对该论文的阅读理解问题，并对答案做轻量级关键词自检。

运行:
    python run_test.py
"""
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

from rlm import RLM

DOC_PATH = Path(__file__).parent / "Recursive_Language_Models.md"


@dataclass(frozen=True)
class TestCase:
    """一个阅读理解测试样例。"""

    query: str
    # 答案中预期出现的关键词（任一命中即视为"看起来合理"，仅作冒烟检查）
    expect_any: List[str] = field(default_factory=list)


TEST_CASES: List[TestCase] = [
    TestCase(
        query="What is RLM (Recursive Language Model)? Summarize the core idea in two sentences.",
        expect_any=["recursi", "prompt", "context", "decompose", "sub"],
    ),
    TestCase(
        query=(
            "On GPT-5, by what median percentage does RLM outperform compaction, "
            "CodeAct with sub-calls, and Claude Code respectively?"
        ),
        expect_any=["26", "130", "13"],
    ),
    TestCase(
        query="What is the name of the post-trained small RLM model, and which base model does it build on?",
        expect_any=["Qwen3-8B", "Qwen", "28"],
    ),
    TestCase(
        query="Who are the authors of this paper and which institution are they from?",
        expect_any=["Zhang", "Kraska", "Khattab", "MIT"],
    ),
]


def run() -> int:
    """运行全部测试样例，返回进程退出码。"""
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if not DOC_PATH.exists():
        print(f"找不到测试文档: {DOC_PATH}")
        return 1

    context = DOC_PATH.read_text(encoding="utf-8")
    print(f"已加载文档: {DOC_PATH.name}（{len(context)} 字符）\n")

    # 与 main.py 的默认模型保持一致
    rlm = RLM(model="openai/gpt-5.5", sub_model="openai/gpt-5.4-mini")
    passed = 0

    for i, case in enumerate(TEST_CASES, 1):
        print("=" * 70)
        print(f"[{i}/{len(TEST_CASES)}] {case.query}")
        print("=" * 70)

        answer = rlm.completion(context, case.query, verbose=False)
        print(f"\n答案:\n{answer}\n")

        # 答案可能是 dict/list 等对象，统一转成字符串再做关键词冒烟自检
        answer_text = str(answer) if answer is not None else ""
        ok = answer is not None and any(
            kw.lower() in answer_text.lower() for kw in case.expect_any
        )
        status = "✅ PASS" if ok else "⚠️  CHECK"
        print(f"自检（命中任一关键词 {case.expect_any}）: {status}\n")
        passed += int(ok)

    print("=" * 70)
    print(f"自检通过: {passed}/{len(TEST_CASES)}")
    print("=" * 70)
    # 自检仅为冒烟提示，不代表答案严格正确；只要全部跑完即视为运行成功。
    return 0


if __name__ == "__main__":
    sys.exit(run())
