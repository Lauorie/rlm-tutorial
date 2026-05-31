// 内置样例轨迹：由后端 demo 生成、随前端打包，保证零网络也能完整演示。
import findSecret from './find-secret.json'
import recursiveSummary from './recursive-summary.json'
import type { Trajectory } from '../lib/types'

export interface Sample {
  id: string
  title: string
  desc: string
  trajectory: Trajectory
}

export const SAMPLES: Sample[] = [
  {
    id: 'find-secret',
    title: '在长日志里找 SECRET',
    desc: '完整 RLM 循环：peek → 正则定位 → 交卷。展示"代码 peek 而非整段喂入"。',
    trajectory: findSecret as unknown as Trajectory,
  },
  {
    id: 'recursive-summary',
    title: '递归摘要（含子调用）',
    desc: '父 RLM 把文档按章节拆开，对每章 rlm_query 起子 RLM，再汇总。展示符号递归。',
    trajectory: recursiveSummary as unknown as Trajectory,
  },
]
