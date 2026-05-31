// 调用后端 /api/rlm 在线跑一次 RLM，返回轨迹。
// 在线运行是"加分项"：即使后端不可用，前端用内置样例也能完整工作。

import type { Trajectory } from './types'

export interface RunRequest {
  scenario: string // 预设场景 id，如 "find-secret" / "recursive-summary"
  use_real?: boolean
}

export async function runRlm(req: RunRequest): Promise<Trajectory> {
  const resp = await fetch('/api/rlm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!resp.ok) {
    const detail = await resp.text().catch(() => '')
    throw new Error(`后端返回 ${resp.status}：${detail || '在线运行失败'}`)
  }
  return (await resp.json()) as Trajectory
}
