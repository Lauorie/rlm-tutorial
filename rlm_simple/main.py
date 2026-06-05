"""RLM 命令行入口。

用法示例:
    python main.py --doc Recursive_Language_Models.md \
        --query "What is the median improvement of RLM over compaction on GPT-5?"
"""
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

from rlm import RLM


def _read_document(path: Path) -> str:
    """读取文本文件作为上下文。

    Args:
        path: 文档路径。

    Returns:
        文档全文。

    Raises:
        FileNotFoundError: 文件不存在时抛出。
    """
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logging.error("找不到文档: %s", path)
        raise


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="用 RLM（递归语言模型）对长文档做阅读理解问答。"
    )
    parser.add_argument(
        "--doc",
        type=Path,
        required=True,
        help="长文本文档路径（如 Recursive_Language_Models.md）",
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="要回答的问题",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="deepseek/deepseek-v4-pro",
        help="主控 LLM 模型名（默认 deepseek/deepseek-v4-pro）",
    )
    parser.add_argument(
        "--sub-model",
        type=str,
        default="deepseek/deepseek-v4-flash",
        help="递归子 LLM 模型名（默认 deepseek/deepseek-v4-flash）",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=8,
        help="主控循环最大迭代轮数（默认 8）",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="安静模式：只输出最终答案，不打印迭代过程",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    """CLI 主函数。"""
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(message)s",
    )
    # 静音底层 HTTP 库的请求日志，让 RLM 的迭代过程更清晰
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    context = _read_document(args.doc)
    logging.info("已加载文档 %s（%d 字符）", args.doc, len(context))

    rlm = RLM(
        model=args.model,
        sub_model=args.sub_model,
        max_iterations=args.max_iterations,
    )
    answer = rlm.completion(context, args.query, verbose=not args.quiet)

    print("\n" + "=" * 60)
    print("问题:", args.query)
    print("=" * 60)
    print(answer if answer is not None else "（未能得出答案）")

    return 0 if answer is not None else 1


if __name__ == "__main__":
    sys.exit(main())
