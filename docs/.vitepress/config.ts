import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

// 站点配置：从零到一实现一个递归语言模型（RLM）
// 用 withMermaid 包裹，让 ```mermaid 代码块直接渲染成架构图/时序图/流程图。
export default withMermaid(
  defineConfig({
    lang: 'zh-CN',
    title: 'RLM 从零到一',
    description: '递归语言模型（Recursive Language Models）的原理与实现：从概念到亲手复现一个 mini-RLM',
    lastUpdated: true,
    cleanUrls: true,
    ignoreDeadLinks: true,

    head: [
      ['meta', { name: 'theme-color', content: '#10b981' }],
      ['meta', { name: 'og:title', content: 'RLM 从零到一' }],
      ['meta', { name: 'og:description', content: '从概念到亲手复现一个递归语言模型' }],
    ],

    themeConfig: {
      outline: { level: [2, 3], label: '本页目录' },
      docFooter: { prev: '上一篇', next: '下一篇' },
      returnToTopLabel: '回到顶部',
      sidebarMenuLabel: '目录',
      darkModeSwitchLabel: '主题',
      lightModeSwitchTitle: '切换到浅色模式',
      darkModeSwitchTitle: '切换到深色模式',

      nav: [
        { text: '首页', link: '/' },
        { text: '开始学习', link: '/00-intro/what-you-will-build' },
        { text: '🚀 在线 Demo', link: '/70-run-deploy/online-demo' },
        {
          text: '参考',
          items: [
            { text: 'RLM 论文', link: 'https://arxiv.org/abs/2512.24601' },
            { text: '官方代码', link: 'https://github.com/alexzhang13/rlm' },
          ],
        },
      ],

      sidebar: [
        {
          text: 'Part 0 · 引言与准备',
          collapsed: false,
          items: [
            { text: '你将做出什么', link: '/00-intro/what-you-will-build' },
            { text: '环境准备（零成本起步）', link: '/00-intro/setup' },
          ],
        },
        {
          text: 'Part 1 · 概念篇：为什么需要 RLM',
          collapsed: false,
          items: [
            { text: '长上下文的根本困境', link: '/10-concepts/long-context-problem' },
            { text: '现有方案的天花板', link: '/10-concepts/existing-approaches' },
            { text: 'RLM 的核心洞察', link: '/10-concepts/rlm-insight' },
            { text: '三个关键设计决策', link: '/10-concepts/three-design-choices' },
          ],
        },
        {
          text: 'Part 2 · 论文原理拆解',
          collapsed: true,
          items: [
            { text: '形式化定义与 Algorithm 1', link: '/20-paper/algorithm' },
            { text: 'REPL 循环时序图', link: '/20-paper/repl-loop' },
            { text: '递归深度与实验结论', link: '/20-paper/depth-and-results' },
          ],
        },
        {
          text: 'Part 3 · 官方源码链路精读',
          collapsed: true,
          items: [
            { text: '三层架构鸟瞰', link: '/30-source/architecture-overview' },
            { text: '核心循环 core/rlm.py', link: '/30-source/core-loop' },
            { text: 'REPL 环境与提示词', link: '/30-source/repl-and-prompts' },
          ],
        },
        {
          text: 'Part 4 · 渐进式 Demo（动手）',
          collapsed: true,
          items: [
            { text: '总览与运行方式', link: '/40-demos/overview' },
            { text: 'Demo 1 · 会记住变量的 REPL', link: '/40-demos/demo1-persistent-repl' },
            { text: 'Demo 2 · 抠出代码并执行', link: '/40-demos/demo2-parse-and-run' },
            { text: 'Demo 3 · 让 REPL 调用 LLM', link: '/40-demos/demo3-llm-query' },
            { text: 'Demo 4 · 完整 RLM 循环', link: '/40-demos/demo4-full-loop' },
            { text: 'Demo 5 · 符号递归', link: '/40-demos/demo5-recursion' },
          ],
        },
        {
          text: 'Part 5 · 从零实现 mini-RLM 后端',
          collapsed: true,
          items: [
            { text: '项目结构与设计取舍', link: '/50-build-backend/structure' },
            { text: '核心包逐文件实现', link: '/50-build-backend/implementation' },
            { text: '日志、护栏与测试', link: '/50-build-backend/logging-and-tests' },
          ],
        },
        {
          text: 'Part 6 · React 可视化前端',
          collapsed: true,
          items: [
            { text: '轨迹数据结构与接口', link: '/60-build-frontend/data-and-api' },
            { text: '三面板可视化器实现', link: '/60-build-frontend/visualizer' },
          ],
        },
        {
          text: 'Part 7 · 运行与部署',
          collapsed: true,
          items: [
            { text: '本地全链路跑起来', link: '/70-run-deploy/run-local' },
            { text: '在线 Demo', link: '/70-run-deploy/online-demo' },
            { text: '部署到 Vercel', link: '/70-run-deploy/deploy-vercel' },
          ],
        },
        {
          text: 'Part 8 · 扩展方向',
          collapsed: true,
          items: [
            { text: '扩展与调试清单', link: '/80-extend/extend-and-debug' },
          ],
        },
      ],

      socialLinks: [
        { icon: 'github', link: 'https://github.com/alexzhang13/rlm' },
      ],

      footer: {
        message: '基于 RLM 论文与官方代码的教学项目 · 仅供学习',
        copyright: 'MIT Licensed',
      },

      search: { provider: 'local' },
    },

    mermaid: {
      theme: 'default',
    },
  })
)
