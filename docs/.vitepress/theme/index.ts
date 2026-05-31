import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import './custom.css'

// 暂时直接复用默认主题；后续在 Part 6/7 会在这里注册自定义组件（如 Demo 嵌入页）。
export default {
  extends: DefaultTheme,
} satisfies Theme
