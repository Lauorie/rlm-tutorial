# rlm_simple —— 递归语言模型最小实现

这是论文 [Recursive Language Models](https://github.com/alexzhang13/rlm)（MIT CSAIL）的一个**极简、用来学习**的复现。

> 一句话原理：当文档太长、塞不进模型的上下文窗口时，**不要**硬塞。
> 而是把长文档放进一个 Python REPL 环境里，让主 LLM **写代码**去把文档切块，
> 再用 `await llm_query()` 递归调用子 LLM（可 `asyncio.gather` 并行）处理每一块，
> 最后调用 `FINAL(...)` 把结果（字符串、dict、list 等任意 Python 对象）交回来。

整个项目只有几百行，没有任何框架，适合一边读一边学。



## 1. 工作原理（看懂这张图就够了）

```
你的问题 + 一篇 159KB 的长文档
        │
        ▼
┌─────────────────────────────────────────────┐
│  主控 LLM（rlm.py 里的循环）                  │
│  它看不到全文，只知道"文档存在 context 变量里" │
│                                               │
│  每一轮它可以：                                │
│   ① 写 ```repl 代码块  →  在异步 REPL 里执行    │
│   ② 看到代码的打印输出  →  决定下一步           │
│   ③ 在代码里调用 FINAL(答案) → 结束并交回结果   │
└───────────────┬───────────────────────────────┘
                │ 在 REPL 里它能 await 调用
                ▼
        await llm_query("处理这一块文本...")   # 可 asyncio.gather 并行
                │
                ▼
        子 LLM（递归的那一层，处理单块）
```

主控 LLM 典型的做法是：先 `print(len(context))` 看文档多长 → 把文档切成几块 →
对每块 `await llm_query()` 抽取相关信息（多块用 `asyncio.gather` 并行）→
汇总 → 在代码里 `FINAL(答案)`。

> **关键点**：`llm_query` 是**异步**的（必须 `await`）；`FINAL` 是 REPL 里的一个
> **函数**，直接在代码里调用，它能交回任意 Python 对象（不止字符串）；REPL 像
> Jupyter，变量在多轮之间一直保留。



## 2. 文件结构

| 文件 | 作用 | 大概多少行 |
|------|------|-----------|
| `rlm.py` | 核心：主控循环 + 异步 `llm_query` + 检测 `FINAL()` | ~165 |
| `repl.py` | 异步 Python 沙箱（支持顶层 `await`、`FINAL` 函数、变量持久化） | ~95 |
| `llm.py` | OpenAI SDK 的薄封装（带自动选模型） | ~100 |
| `sys_prompt.py` | 给主控 LLM 的系统提示词（教它怎么用 REPL） | ~160 |
| `main.py` | 命令行入口：对任意文档提任意问题 | ~125 |
| `run_test.py` | 演示：拿论文本身做 4 个阅读理解问题 | ~100 |

建议阅读顺序：`sys_prompt.py`（理解规则）→ `rlm.py`（理解循环）→ `repl.py` → `llm.py`。



## 3. 安装

```bash
# 1) 安装依赖（只有两个）
pip install -r requirements.txt

# 2) 配置 API（在项目根目录建一个 .env 文件）
```

`.env` 文件内容示例：

```bash
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://你的中转地址/v1   # 用官方 OpenAI 可省略这一行
```

> `model` 默认是 `auto`：启动时会自动选用 API 返回的第一个可用模型。
> 你也可以用 `--model` 手动指定。



## 4. 快速开始

### 方式一：一键演示（推荐先跑这个）

直接拿论文 `Recursive_Language_Models.md` 当长文本，跑 4 个内置问题：

```bash
python run_test.py
```

它会依次问"作者是谁""RLM 相比基线提升多少"等问题，并对答案做一个**关键词冒烟自检**
（只是粗略检查答案里有没有出现预期关键词，不代表严格判分）。

### 方式二：自己提问（命令行）

```bash
python3 main.py \
  --doc Recursive_Language_Models.md \
  --query "What is the median improvement of RLM over compaction on GPT-5?"
```

你会看到 RLM 一轮轮地在 REPL 里探查文档，最后给出答案。

常用参数：

| 参数 | 说明 | 默认 |
|------|------|------|
| `--doc` | 长文本文档路径 | 必填 |
| `--query` | 你的问题 | 必填 |
| `--model` | 主控 LLM 模型 | `gpt-5.5` |
| `--sub-model` | 递归子 LLM 模型 | `gpt-5.4-mini` |
| `--max-iterations` | 最多迭代几轮 | `5` |
| `--quiet` | 只打印最终答案，不显示过程 | 关 |

只想看答案、不看过程：

```bash
python3 main.py --doc Recursive_Language_Models.md --query "你的问题" --quiet
```

### 方式三：在代码里调用

```python
from rlm import RLM   # 在项目目录里运行

rlm = RLM()
context = open("Recursive_Language_Models.md", encoding="utf-8").read()
answer = rlm.completion(context, "Summarize the core idea of RLM.", verbose=True)
print(answer)
```



## 5. 自己换一篇长文档来测

`--doc` 接受任意 `.md` / `.txt` 文本文件，所以你可以拿任何长文档来玩：

```bash
python main.py --doc 我的小说.txt --query "主角最后的结局是什么？"
```



## 6. 常见问题

**Q: 报错"未找到 API Key"？**
A: 检查根目录下有没有 `.env`，里面是否写了 `OPENAI_API_KEY`。

**Q: 跑到"达到最大迭代轮数仍未给出最终答案"？**
A: 主控 LLM 兜圈子了。可以调大 `--max-iterations`，或换一个更强的 `--model`。

**Q: `FINAL()` 是什么？怎么生效的？**
A: `FINAL` 是 REPL 环境里预置的一个**函数**。主控 LLM 在它写的 `repl` 代码里
直接调用 `FINAL(答案)` 即可提交结果——`repl.py` 一旦发现 `FINAL()` 被调用，就记下
答案并结束循环。注意是 `FINAL(变量名)` 而**不是** `FINAL("变量名")`（后者会把字符串
本身当答案）。`FINAL` 能交回任意 Python 对象，比如 `FINAL({"作者": [...]})`。

**Q: `llm_query` 为什么要 `await`？能并行吗？**
A: `llm_query` 是异步函数，所以在 REPL 里必须写 `await llm_query(...)`。想同时跑多个
子查询（更快）就用 `await asyncio.gather(*tasks)`——底层用线程池真正并行调用 API。

**Q: 安全吗？`repl.py` 会执行模型写的代码。**
A: 这是 RLM 范式的核心——主控 LLM 必须能执行自己写的代码。
**仅供学习/可信环境使用**，不要把它接到不可信输入上。



## 7. 这个精简版相比原始代码修了什么

- 原来用相对导入但没有入口脚本，**根本跑不起来** → 改为可直接运行
- REPL 从同步 `exec` 升级为**异步沙箱**：支持顶层 `await`、`asyncio.gather` 并行，
  且变量像 Jupyter 一样跨轮持久化
- `FINAL` 改为 REPL 里的**函数**：模型在代码里 `FINAL(value)` 即提交答案，
  可交回任意 Python 对象（dict/list/数字/字符串）
- `llm_query` 改为**异步**，用线程池让多个子查询真正并行
- `print()` 调试 → 换成标准 `logging`（并静音底层 HTTP 日志）
- 补了 `main.py` / `run_test.py` / `requirements.txt` 和这份 README
