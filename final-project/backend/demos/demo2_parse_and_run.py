"""Demo 2 · 从模型输出里抠出代码并执行

要解决的问题：模型不会"直接调用函数"。它只会输出一段文本。RLM 的约定是：
模型把想执行的动作写在 ```repl 代码块里。所以我们需要：

  1. find_code_blocks：用正则从一坨文本里把所有 ```repl 块抠出来。
  2. 逐块丢进 REPL 执行，拿到 stdout。
  3. 把执行结果格式化，准备回喂给模型（截断超长部分）。

这个 demo 手写一段"假装是模型输出"的文本，跑通"解析 → 执行 → 格式化反馈"这一环。
它是 RLM 主循环里最核心的一步，只是这里我们先不接真模型。

运行：
    python demos/demo2_parse_and_run.py
"""

import os
import sys
# 让本脚本无需安装即可找到 mini_rlm 包（加入上一级目录到 sys.path）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_rlm import MiniREPL, MockLM
from mini_rlm.parsing import find_code_blocks, format_iteration_feedback
from mini_rlm.types import CodeBlock

# 假装这是模型某一轮的输出：有自然语言思考，也有两个 ```repl 块
FAKE_MODEL_OUTPUT = """\
我先看看 context 有多长，再统计里面 "ERROR" 出现了几次。

```repl
print("长度:", len(context))
```

顺便统计一下错误行数：

```repl
errors = context.count("ERROR")
print("ERROR 出现次数:", errors)
```

普通的 ```python 块不算动作，不会被执行：

```python
print("我不该被执行")
```
"""


def main() -> None:
    repl = MiniREPL(client=MockLM(responses=["unused"]))
    repl.load_context("INFO ok\nERROR disk full\nINFO ok\nERROR oom\nINFO ok\n")

    print("=" * 60)
    print("第 1 步：从模型输出里抠 ```repl 代码块")
    print("=" * 60)
    blocks = find_code_blocks(FAKE_MODEL_OUTPUT)
    print(f"抠到 {len(blocks)} 个代码块（注意 ```python 块被正确忽略了）:")
    for i, b in enumerate(blocks):
        print(f"  [{i + 1}] {b!r}")

    print("\n" + "=" * 60)
    print("第 2 步：逐块执行，收集结果")
    print("=" * 60)
    code_blocks: list[CodeBlock] = []
    for b in blocks:
        result = repl.execute_code(b)
        code_blocks.append(CodeBlock(code=b, result=result))
        print(f"执行 {b!r} -> stdout: {result.stdout.strip()!r}")

    print("\n" + "=" * 60)
    print("第 3 步：格式化成回喂给模型的反馈（下一轮 user 消息）")
    print("=" * 60)
    feedback = format_iteration_feedback(code_blocks, truncate_chars=200)
    print(feedback)

    print("\n小结：'解析 ```repl → 执行 → 格式化反馈' 就是 RLM 主循环的一次心跳。")
    print("Demo 4 会把这一环和真正的模型调用接起来，形成完整循环。")


if __name__ == "__main__":
    main()
