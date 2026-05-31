import type { TrajectoryMetadata } from '../lib/types'

// 顶部四个统计卡片：迭代 / 代码块 / 子调用 / 耗时
export function StatCards({ meta }: { meta: TrajectoryMetadata }) {
  const cards = [
    { label: '迭代轮数', value: meta.total_iterations, icon: '◎', cls: 'c-green' },
    { label: '代码块', value: meta.total_code_blocks, icon: '⟨⟩', cls: 'c-blue' },
    { label: '子调用', value: meta.total_sub_calls, icon: '◇', cls: 'c-violet' },
    { label: '耗时(s)', value: meta.total_execution_time.toFixed(3), icon: '⏱', cls: 'c-amber' },
  ]
  return (
    <div className="stat-cards">
      {cards.map((c) => (
        <div key={c.label} className={`stat ${c.cls}`}>
          <span className="stat-icon">{c.icon}</span>
          <div>
            <div className="stat-value">{c.value}</div>
            <div className="stat-label">{c.label}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
