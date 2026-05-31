"""Demo 1 · 一个会记住变量的 REPL

要解决的问题：RLM 的第一块基石是"环境 E"——一个能跨多次执行记住状态的 Python REPL。
这个 demo 不涉及任何 LLM，只让你亲眼看到 MiniREPL 的三个核心能力：

  1. 持久化：第一次执行建的变量，第二次执行还在。
  2. stdout 捕获：print 的东西被收集起来（将来要回喂给模型）。
  3. context 卸载：超长输入作为 `context` 变量存在，只能用代码去 peek。
  4. answer 终止：设置 answer["ready"]=True 就能"交卷"。

运行：
    python demos/demo1_persistent_repl.py
"""

import os
import sys
# 让本脚本无需安装即可找到 mini_rlm 包（加入上一级目录到 sys.path）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_rlm import MiniREPL, MockLM


def main() -> None:
    # MiniREPL 需要一个 client 给 llm_query 用，这个 demo 用不到，随便给个 mock
    repl = MiniREPL(client=MockLM(responses=["unused"]))

    # 把一段"超长输入"卸载进 REPL —— 注意它没有进入任何模型上下文，只是个变量
    repl.load_context("噪声 " * 50 + "PASSWORD=hunter2 " + "噪声 " * 50)

    print("=" * 60)
    print("第 1 次执行：建一个变量 + peek context 的长度")
    print("=" * 60)
    r1 = repl.execute_code(
        "n = len(context)\n"
        "print('context 共', n, '个字符')\n"
        "print('开头 20 字:', context[:20])"
    )
    print("stdout >>>", r1.stdout.strip())

    print("\n" + "=" * 60)
    print("第 2 次执行：复用上一次建的变量 n（这就是 REPL 的持久化）")
    print("=" * 60)
    r2 = repl.execute_code("print('上次算出的 n 还在:', n)")
    print("stdout >>>", r2.stdout.strip())

    print("\n" + "=" * 60)
    print("第 3 次执行：用代码在 context 里定位 PASSWORD，然后交卷")
    print("=" * 60)
    r3 = repl.execute_code(
        "import re\n"
        "m = re.search(r'PASSWORD=(\\w+)', context)\n"
        "answer['content'] = m.group(1)\n"
        "answer['ready'] = True"
    )
    print("捕获到最终答案 final_answer =", r3.final_answer)

    print("\n小结：我们没有把 100+ 行 context 喂给任何模型，全程只用代码去 peek/定位。")
    print("这正是 RLM 的起点：把 prompt 当环境，而不是塞进上下文窗口。")


if __name__ == "__main__":
    main()
