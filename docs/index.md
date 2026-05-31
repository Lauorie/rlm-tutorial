---
layout: home

hero:
  name: "RLM 从零到一"
  text: "亲手实现一个递归语言模型"
  tagline: 把超长 prompt 当成环境，而不是喂给神经网络 —— 用一个 REPL + 递归自调用，突破上下文窗口限制
  actions:
    - theme: brand
      text: 开始学习 →
      link: /00-intro/what-you-will-build
    - theme: alt
      text: 🚀 在线 Demo
      link: /70-run-deploy/online-demo
    - theme: alt
      text: 论文原理
      link: /10-concepts/rlm-insight

features:
  - icon: 🧠
    title: 先讲清「为什么」
    details: 不是源码逐行翻译。从 context rot 和上下文窗口的根本困境出发，讲清 RLM 每一个设计决策在解决什么问题。
  - icon: 🪜
    title: 由浅入深 5 个 Demo
    details: 从"会记住变量的 REPL"到"符号递归"，每个 Demo 单独可跑、配实验和常见错误，一步步把核心机制握在手里。
  - icon: 🛠️
    title: 从零复现 mini-RLM
    details: 亲手写出一个简化但保留核心思想的递归语言模型：Python 后端核心闭环 + 递归子调用 + React 轨迹可视化前端。
  - icon: 💸
    title: 零成本起步
    details: 内置 MockLM，不需要任何 API key 就能跑通完整 RLM 循环和可视化。想用真实模型？配一个 OpenAI 兼容的 key 即可。
  - icon: 📊
    title: 图说一切
    details: 大量 Mermaid 架构图、时序图、模块关系图、概念对比表，把抽象的递归执行流变成看得见的东西。
  - icon: 🚀
    title: 一键部署
    details: 教程站点 + 在线 Demo 一体化，构建后一次部署到 Vercel，后端走 Serverless，前端静态托管。
---

## 这套教程适合谁

你是一名**计算机本科毕业生**或有同等基础的开发者：会写 Python、了解基本的 Web 前后端、用过 LLM API，但**没读过 RLM 论文、也没接触过"把 prompt 当环境"这套思路**。

读完这套教程，你将能够：

- 用自己的话解释 **RLM 为什么能处理超过模型上下文窗口 10 倍以上的输入**；
- 说清 **REPL 卸载、符号递归、`answer` 终止信号** 这三件事各自解决了什么；
- 从零写出一个**能跑、能可视化、能递归**的 mini-RLM，并部署上线。

## 学习路线图

```mermaid
flowchart LR
    A[Part 1<br/>概念篇<br/>为什么需要 RLM] --> B[Part 2<br/>论文原理<br/>Algorithm 1]
    B --> C[Part 3<br/>源码精读<br/>官方实现链路]
    C --> D[Part 4<br/>5 个渐进 Demo<br/>动手握住机制]
    D --> E[Part 5<br/>mini-RLM 后端<br/>核心闭环+递归]
    E --> F[Part 6<br/>React 可视化<br/>看见递归执行]
    F --> G[Part 7<br/>运行与部署<br/>Vercel 上线]
    G --> H[Part 8<br/>扩展方向]

    style A fill:#d1fae5,stroke:#10b981
    style E fill:#dbeafe,stroke:#3b82f6
    style F fill:#dbeafe,stroke:#3b82f6
    style G fill:#fef3c7,stroke:#f59e0b
```

> 💡 **建议**：第一遍按顺序读 Part 1 → Part 4，把概念和机制握住；动手时直接对照 `final-project/` 里的可运行代码。赶时间的话，可以先看[你将做出什么](/00-intro/what-you-will-build)和[在线 Demo](/70-run-deploy/online-demo)建立直觉，再回头补原理。
