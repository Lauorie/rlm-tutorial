# RLM 从零到一 · 递归语言模型教学项目

一套**完整可运行**的中文教学项目，带你从概念到亲手复现一个**递归语言模型（Recursive Language Model, RLM）**——把超长 prompt 当作环境、让模型写代码去递归处理它，从而突破上下文窗口限制。

> 配套论文：[Recursive Language Models](https://arxiv.org/abs/2512.24601) · 官方代码：[alexzhang13/rlm](https://github.com/alexzhang13/rlm)

本项目包含三部分，一次部署即可同时上线**教程站点 + 在线可视化 Demo**：

| 部分 | 技术栈 | 说明 |
|---|---|---|
| 📖 教程站点 | VitePress | 18+ 章渐进式教程，含 Mermaid 图、源码精读、5 个 Demo |
| 🐍 后端 `mini_rlm` | Python（纯标准库） | 简化但保留核心思想的 RLM：核心闭环 + 符号递归 + MockLM + 轨迹日志 |
| ⚛️ 前端可视化器 | React + Vite | 把 RLM 执行轨迹画成迭代时间线 + 代码执行 + 递归子调用 |

## 目录结构

```text
rlm-tutorial/
├── docs/                       # VitePress 教程站点（Part 0–8）
│   ├── .vitepress/config.ts    # 导航/侧边栏/Mermaid/中文主题
│   └── public/demo/            # React 前端构建产物（被 iframe 内嵌；构建时生成）
├── final-project/
│   ├── backend/                # 后端 mini_rlm（可独立运行）
│   │   ├── mini_rlm/           # 核心包（7 个文件）
│   │   ├── demos/              # 5 个渐进式 Demo
│   │   ├── tests/              # 21 个测试，全用 MockLM 零成本
│   │   ├── scenarios.py        # 在线 Demo 预设场景（serverless/本地共用）
│   │   └── server.py           # 本地 FastAPI 开发服务
│   └── frontend/               # React 可视化器
├── api/rlm.py                  # Vercel Python Serverless 入口
├── vercel.json                 # 一次部署：静态站点 + 内嵌 Demo + serverless
└── requirements.txt            # serverless 依赖（仅 use_real 时用到 openai）
```

## 快速开始

### 零成本跑通后端（无需任何 API key）

```bash
cd final-project/backend
uv venv --python 3.12 && source .venv/bin/activate
uv pip install pytest
pytest -q                              # 期望 21 passed
python demos/demo1_persistent_repl.py  # 看持久化 REPL
python demos/demo5_recursion.py        # 看符号递归
```

### 跑教程站点

```bash
npm install
npm run docs:dev          # http://localhost:5173
```

### 跑前端可视化器（自带样例，可离线浏览）

```bash
cd final-project/frontend && npm install && npm run dev
# 想体验"在线运行"：另开终端跑本地 API
cd final-project/backend && uv pip install -e ".[api]" && uvicorn server:app --port 8000
```

## 部署到 Vercel

```bash
npm run build     # 本地验证：先构建前端进 docs/public/demo，再构建 VitePress
```

把仓库连到 Vercel 即可（或 `vercel` CLI）。`vercel.json` 已配好：

- `buildCommand` 跑 `npm run build`（前端 → `docs/public/demo` → VitePress）
- `outputDirectory` 指向 `docs/.vitepress/dist`
- `functions.includeFiles` 把 `final-project/backend` 打进 serverless 函数，供 `api/rlm.py` 导入 `mini_rlm`
- 想让在线 Demo 跑真实模型：在 Vercel 环境变量配 `OPENAI_API_KEY`（默认走 MockLM，零配置、避免 serverless 超时）

详见教程 [Part 7 · 部署到 Vercel](./docs/70-run-deploy/deploy-vercel.md)。

## 学习路线

概念（为什么需要 RLM）→ 论文原理 → 官方源码精读 → 5 个渐进 Demo → 从零实现 mini-RLM 后端 → React 可视化前端 → 运行与部署 → 扩展方向。

建议从 [docs/00-intro/what-you-will-build.md](./docs/00-intro/what-you-will-build.md) 开始。

## 致谢与许可

教学内容基于 Alex L. Zhang 等人的 RLM 论文与官方开源实现，仅供学习。MIT License。
