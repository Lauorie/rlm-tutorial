# mini-rlm

一个**简化但保留核心思想**的递归语言模型（Recursive Language Model）教学实现。

配套教程见仓库根目录的 VitePress 站点（`/docs`）。本目录是可独立运行的 Python 后端。

## 它保留了什么

- **核心闭环**：REPL 持久化执行 + `context` 卸载 + ` ```repl ` 代码块解析 + `llm_query` + `answer` 终止信号 + 迭代循环 + stdout 截断。
- **符号递归**：`rlm_query` + `max_depth` 控制的递归子调用。
- **零成本**：内置 `MockLM`，无需任何 API key 就能跑通完整循环。
- **轨迹日志**：JSONL 格式，可直接喂给前端可视化器。

## 快速开始

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"          # 只跑核心+测试，无需 openai
pytest -q                           # 全部用 MockLM，零成本

# 想用真实模型？
uv pip install -e ".[openai]"
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=...           # 可选，指向兼容服务/国内代理
python demos/demo4_full_loop.py --real
```

## 最小用法

```python
from mini_rlm import MiniRLM, RLMConfig, MockLM

mock = MockLM(responses=[
    "```repl\nprint(len(context))\n```",
    "```repl\nanswer['content'] = 'done'\nanswer['ready'] = True\n```",
])
rlm = MiniRLM(config=RLMConfig(max_iterations=4), client=mock)
print(rlm.completion(context="hello" * 100, task="统计").response)
```

## 模块速览

| 文件 | 职责 |
|------|------|
| `types.py` | 数据类型（嵌套轨迹结构，对齐前端） |
| `parsing.py` | 解析 ` ```repl ` 代码块 + 截断 |
| `prompts.py` | 把普通 LLM 调教成 RLM 的系统提示词 |
| `clients.py` | `BaseLM` / `OpenAICompatClient` / `MockLM` |
| `repl.py` | `MiniREPL`：持久化执行 + 工具注入 + 答案捕获 |
| `rlm.py` | `MiniRLM`：主循环 + 递归 |
| `logger.py` | JSONL 轨迹日志 |

> ⚠️ `MiniREPL` 用 `exec` 在本进程执行模型生成的代码，**不是安全沙箱**。生产环境请用 Docker/E2B/Modal 等隔离。
