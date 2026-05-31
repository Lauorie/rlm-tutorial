"""Demo 5 · 符号递归（rlm_query + depth）

要解决的问题：llm_query 开的子模型没有 REPL、没有记忆，只能处理"一小段、一步到位"的
任务。但如果某个子任务本身又很长、很复杂呢？答案是：让子调用本身也是一个完整的 RLM。

这就是 `rlm_query`：当递归深度还没到 max_depth 时，它会新建一个 depth+1 的 MiniRLM
（有自己的 REPL、自己的循环、还能再 rlm_query）。这正是论文标题里的"Recursive"。

depth 的语义：
  - max_depth=1：rlm_query 退化成普通 llm_query（叶子，无子 REPL）。
  - max_depth=2：rlm_query 能起一层子 RLM。
  - max_depth=N：能递归 N-1 层。

这个 demo 用 MockLM 编排一个两层递归：父 RLM 把一篇"长文档"按章节拆开，对每个章节
用 rlm_query 起一个子 RLM 去总结，最后把子总结拼成全文摘要。

零成本运行：
    python demos/demo5_recursion.py
"""

import os
import sys
# 让本脚本无需安装即可找到 mini_rlm 包（加入上一级目录到 sys.path）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_rlm import MiniRLM, MockLM, RLMConfig, TrajectoryLogger


def build_shared_mock() -> MockLM:
    """父子共享一个脚本 MockLM；responses 必须按'实际调用发生的顺序'排列。

    调用顺序（关键！）：
      1. 父 RLM 第 1 轮：写代码，对 2 个章节分别 rlm_query
      2.   -> 子 RLM A 第 1 轮：交卷（章节1摘要）
      3.   -> 子 RLM B 第 1 轮：交卷（章节2摘要）
      4. 父 RLM 第 2 轮：拼接并交卷
    """
    return MockLM(
        responses=[
            # 1. 父第 1 轮：对每个章节起子 RLM
            "我把文档按章节拆开，每节交给一个子 RLM 去总结。\n"
            "```repl\n"
            "chapters = context.split('###')\n"
            "chapters = [c.strip() for c in chapters if c.strip()]\n"
            "summaries = []\n"
            "for ch in chapters:\n"
            "    s = rlm_query(f'用一句话总结这段：{ch}')\n"
            "    summaries.append(s)\n"
            "    print('得到子摘要:', s)\n"
            "```",
            # 2. 子 RLM A：直接交卷
            "```repl\n"
            "answer['content'] = '章节1讲了 RLM 把 prompt 当环境'\n"
            "answer['ready'] = True\n"
            "```",
            # 3. 子 RLM B：直接交卷
            "```repl\n"
            "answer['content'] = '章节2讲了符号递归突破上下文窗口'\n"
            "answer['ready'] = True\n"
            "```",
            # 4. 父第 2 轮：拼接并交卷
            "```repl\n"
            "answer['content'] = ' | '.join(summaries)\n"
            "answer['ready'] = True\n"
            "```",
        ]
    )


def main() -> None:
    context = (
        "### 第一章\nRLM 的核心是把超长 prompt 放进 REPL 当变量。\n"
        "### 第二章\nRLM 通过 rlm_query 递归调用自己来处理子任务。\n"
    )

    logger = TrajectoryLogger(log_dir="./logs")
    rlm = MiniRLM(
        config=RLMConfig(max_iterations=6, max_depth=2),  # 允许一层递归
        client=build_shared_mock(),
        trajectory_logger=logger,
    )

    result = rlm.completion(context=context, task="生成全文摘要")

    print("=" * 60)
    print("最终摘要:", result.response)
    print("=" * 60)

    # 把递归结构打印出来：父迭代里嵌着子调用，子调用又有自己的迭代
    print("\n递归轨迹结构：")
    for it in result.iterations:
        for b in it.code_blocks:
            for sub in b.result.rlm_calls:
                kind = "叶子 LLM" if sub.stopped_reason == "leaf_llm" else "子 RLM"
                print(f"  └─ depth={sub.depth} [{kind}] 自身迭代数={len(sub.iterations)} "
                      f"-> {sub.response}")

    print("\n小结：父 RLM 在一段代码里 for 循环起了多个子 RLM，每个子 RLM 是独立的完整循环。")
    print("把 max_depth 调成 1 再跑一次，你会看到 rlm_query 退化成叶子 LLM（无子迭代）。")


if __name__ == "__main__":
    main()
