"""Demo 3 · 让 REPL 能调用 LLM（llm_query）

要解决的问题：到目前为止，REPL 只能做"纯计算"（切片、正则、计数）。但很多任务需要
"语义理解"——比如"这段文字的情感是正面还是负面？"。RLM 的杀手锏是：让模型能在代码里
调用另一个模型来处理 context 的某个**切片**。

这就是 `llm_query(prompt) -> str`：开一个全新的、无 REPL、无记忆的子模型，回答你传给它的
prompt。关键用法是——**在循环里对很多切片分别调用它**，从而处理远超单次上下文的内容。

这个 demo 用 MockLM 模拟一个"情感分类子模型"，演示在 REPL 代码里 for 循环逐条调用。
零成本；想看真模型把命令行加 --real 并设好 OPENAI_API_KEY。

运行：
    python demos/demo3_llm_query.py
    python demos/demo3_llm_query.py --real
"""

import os
import sys
# 让本脚本无需安装即可找到 mini_rlm 包（加入上一级目录到 sys.path）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mini_rlm import MiniREPL
from mini_rlm.clients import MockLM, OpenAICompatClient


def make_client(use_real: bool):
    if use_real:
        # 真实模型：任何 OpenAI 兼容服务都行，靠环境变量 OPENAI_API_KEY / OPENAI_BASE_URL
        return OpenAICompatClient(model_name="gpt-4o-mini")

    # Mock 情感分类器：根据 prompt 里的关键词决定返回"正面/负面"
    def classify(messages) -> str:
        text = messages[-1].content
        if any(w in text for w in ["好", "棒", "喜欢", "amazing", "great"]):
            return "正面"
        if any(w in text for w in ["差", "烂", "讨厌", "terrible", "bad"]):
            return "负面"
        return "中性"

    return MockLM(response_fn=classify)


def main() -> None:
    use_real = "--real" in sys.argv
    repl = MiniREPL(client=make_client(use_real))

    # context 是一批待分类的评论
    reviews = [
        "这个产品太棒了，我很喜欢！",
        "质量很差，非常讨厌。",
        "还行吧，没什么特别的。",
    ]
    repl.load_context(reviews)

    print("=" * 60)
    print("在 REPL 代码里 for 循环，对 context 的每一条切片调用 llm_query")
    print("=" * 60)
    code = """
results = []
for i, review in enumerate(context):
    label = llm_query(f"判断这条评论的情感，只回答'正面'/'负面'/'中性'：{review}")
    results.append((review[:12], label))
    print(f"  评论 {i+1}: {label}")
print("分类完成，共", len(results), "条")
"""
    result = repl.execute_code(code)
    print(result.stdout)

    print("=" * 60)
    print(f"这一段代码里一共触发了 {len(result.rlm_calls)} 次子 LLM 调用")
    print("每次调用都是一个全新的、看不到 REPL 的子模型——它只看到你传的那一条评论。")
    print("=" * 60)
    print("\n小结：llm_query 让你把'语义处理'下放给子模型，而且是 programmatic 地、循环地下放。")
    print("如果有 100 万条评论，循环 100 万次即可——这就是 RLM 突破上下文窗口的关键。")


if __name__ == "__main__":
    main()
