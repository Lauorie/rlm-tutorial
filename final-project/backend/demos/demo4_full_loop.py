"""Demo 4 · 完整的 RLM 循环

要解决的问题：前三个 demo 分别造好了零件——持久化 REPL、代码块解析、llm_query。
现在把它们和"真正的模型决策"接起来，形成 Algorithm 1 的完整循环：

    系统提示告诉模型：你的 context 在 REPL 里，写 ```repl 去处理它，set answer 交卷
    循环：模型看历史 → 写代码 → 执行 → 把结果接回历史 → 直到 answer["ready"]=True

这个 demo 用 MockLM 脚本扮演一个"懂 RLM 协议"的模型，完成一个真实任务：
在一段很长的日志里，统计 ERROR 行数并找出第一条 ERROR 的内容。

零成本运行（推荐先跑这个看清楚每一轮）：
    python demos/demo4_full_loop.py

接真模型（需要 OPENAI_API_KEY，可选 OPENAI_BASE_URL）：
    python demos/demo4_full_loop.py --real
"""

import os
import sys
# 让本脚本无需安装即可找到 mini_rlm 包（加入上一级目录到 sys.path）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_rlm import MiniRLM, MockLM, RLMConfig, TrajectoryLogger
from mini_rlm.clients import OpenAICompatClient

# 构造一段"超长" context：1000 行日志，中间藏着若干 ERROR
LOG_LINES = []
for i in range(1000):
    if i == 137:
        LOG_LINES.append(f"[{i}] ERROR database connection refused")
    elif i % 200 == 50:
        LOG_LINES.append(f"[{i}] ERROR timeout on request")
    else:
        LOG_LINES.append(f"[{i}] INFO request handled ok")
CONTEXT = "\n".join(LOG_LINES)

TASK = "这段日志里有多少行 ERROR？第一条 ERROR 的完整内容是什么？"


def scripted_mock() -> MockLM:
    """一个扮演'懂 RLM 协议'的假模型：先 peek，再统计+定位，最后交卷。"""
    return MockLM(
        responses=[
            # 第 1 轮：先探查 context 规模
            "我先看看日志有多大。\n"
            "```repl\n"
            "print('总行数:', context.count(chr(10)) + 1)\n"
            "print('前 80 字:', context[:80])\n"
            "```",
            # 第 2 轮：统计 ERROR 行数并定位第一条
            "现在统计 ERROR 并找第一条。\n"
            "```repl\n"
            "lines = context.split(chr(10))\n"
            "errors = [l for l in lines if 'ERROR' in l]\n"
            "print('ERROR 行数:', len(errors))\n"
            "print('第一条:', errors[0])\n"
            "```",
            # 第 3 轮：组织答案并交卷
            "```repl\n"
            "answer['content'] = f'共 {len(errors)} 行 ERROR；第一条是: {errors[0]}'\n"
            "answer['ready'] = True\n"
            "```",
        ]
    )


def main() -> None:
    use_real = "--real" in sys.argv

    if use_real:
        client = OpenAICompatClient(model_name="gpt-4o-mini")
        config = RLMConfig(model_name="gpt-4o-mini", backend="openai", max_iterations=10)
    else:
        client = scripted_mock()
        config = RLMConfig(model_name="mock-model", max_iterations=10)

    logger = TrajectoryLogger(log_dir="./logs")
    rlm = MiniRLM(config=config, client=client, trajectory_logger=logger)

    print("任务:", TASK)
    print(f"context 规模: {len(CONTEXT)} 字符 / {CONTEXT.count(chr(10)) + 1} 行")
    print("（注意：这段 context 从未整体进入模型上下文，模型全靠写代码 peek）\n")

    result = rlm.completion(context=CONTEXT, task=TASK)

    # 把每一轮发生了什么打出来，方便对照"循环"概念
    for it in result.iterations:
        print(f"--- 第 {it.iteration + 1} 轮 ---")
        print("模型说:", it.response.split("```")[0].strip()[:60] or "(直接写代码)")
        for b in it.code_blocks:
            print("  执行代码:", b.code.replace("\n", " ")[:70])
            if b.result.stdout.strip():
                print("  得到输出:", b.result.stdout.strip().replace("\n", " | ")[:80])
        print()

    print("=" * 60)
    print("最终答案:", result.response)
    print("停止原因:", result.stopped_reason, "| 总迭代:", len(result.iterations))
    print("轨迹已写入 ./logs/，可用 Part 6 的可视化前端打开")


if __name__ == "__main__":
    main()
