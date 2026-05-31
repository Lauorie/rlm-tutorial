# 环境准备（零成本起步）

这一章把你需要的工具一次装好。**好消息**：跑通整个 RLM 核心循环和可视化，**不需要任何 API key、不花一分钱**——我们内置了 `MockLM`。API key 只在你想看真实大模型表现时才需要。

## 你需要装什么

| 工具 | 版本 | 用途 | 必需性 |
|---|---|---|---|
| Python | ≥ 3.10 | 后端 `mini_rlm` | 必需 |
| uv（或 pip） | 最新 | Python 包管理 | 推荐 |
| Node.js | ≥ 18 | VitePress 站点 + React 前端 | 跑前端/站点时需要 |
| git | 任意 | 拉代码、部署 | 必需 |

> uv 是一个快得多的 Python 包管理器。没有也行，用 `pip` + `venv` 一样。

## 第一步：拿到代码

整套教学项目的目录结构长这样（你在 Part 5/6 会逐文件把它建出来，也可以直接克隆现成的）：

```
rlm-tutorial/
├── docs/                    # 你正在看的 VitePress 站点
├── final-project/
│   ├── backend/             # ← 后端 mini_rlm 在这里
│   │   ├── mini_rlm/        # 核心包
│   │   ├── demos/           # 5 个渐进式 Demo
│   │   └── tests/           # MockLM 驱动的测试
│   └── frontend/            # ← React 可视化器
├── api/                     # Vercel Serverless 函数
└── vercel.json              # 部署配置
```

## 第二步：跑通后端（零成本）

```bash
cd final-project/backend

# 用 uv（推荐）
uv venv --python 3.12
source .venv/bin/activate
uv pip install pytest          # 核心是纯标准库，只有测试需要 pytest

# 或者用传统方式
# python -m venv .venv && source .venv/bin/activate
# pip install pytest
```

验证一切正常——**这一步不联网、不花钱**：

```bash
pytest -q
# 期望输出：21 passed
```

再跑第一个 Demo，亲眼看看持久化 REPL：

```bash
python demos/demo1_persistent_repl.py
```

你会看到 REPL 跨多次执行记住了变量、并从一段长文本里定位出 `PASSWORD`——全程没有调用任何真实模型。

::: tip 为什么能零成本？
`MockLM` 是一个"假模型"：你给它一个回复脚本（`responses=[...]`），它就按顺序吐出来。RLM 的循环、REPL、递归逻辑**完全不关心**底下是真模型还是假模型——这正是好的抽象带来的好处。详见 [Demo 4](/40-demos/demo4-full-loop)。
:::

## 第三步（可选）：接真实模型

想看真模型怎么当 RLM？装上 `openai` 客户端并配好 key：

```bash
uv pip install openai

# 用环境变量配置；OPENAI_BASE_URL 可指向任意 OpenAI 兼容服务（含国内代理、本地 vLLM）
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"   # 可改成你的兼容端点

python demos/demo4_full_loop.py --real
```

::: warning 常见错误
- **`ModuleNotFoundError: No module named 'mini_rlm'`**：你没在 `backend/` 目录下，或没激活虚拟环境。Demo 脚本顶部有一段 `sys.path` 引导，正常情况下在 `backend/` 下直接 `python demos/xxx.py` 就能跑。
- **真实模型很慢/超时**：RLM 会多轮调用模型，真实运行可能要几十秒。这是正常的，教学时优先用 MockLM 看清逻辑。
- **把 key 写进代码**：永远别这么做。用环境变量或 `.env`，并确保 `.env` 在 `.gitignore` 里。
:::

## 第四步（可选）：跑前端可视化器

```bash
cd final-project/frontend
npm install
npm run dev          # 打开 http://localhost:5173
```

前端**自带两个样例轨迹**，所以即使不开后端也能完整浏览。想体验"在线运行"按钮，再开一个终端跑本地 API 服务：

```bash
cd final-project/backend
uv pip install -e ".[api]"
uvicorn server:app --reload --port 8000
```

## 第五步（可选）：跑教程站点本身

```bash
# 在仓库根目录
npm install
npm run docs:dev     # 打开 http://localhost:5173
```

## 检查清单

开始学习前，确认这几项至少满足前两个：

- [x] `pytest -q` 输出 `21 passed`（后端核心 OK）
- [x] `python demos/demo1_persistent_repl.py` 能跑出结果（零成本通路 OK）
- [ ] （可选）`--real` 能调通真实模型
- [ ] （可选）前端 `npm run dev` 能打开

准备好了？进入 [Part 1：长上下文的根本困境](/10-concepts/long-context-problem)，搞清楚 RLM 到底在解决什么问题。
