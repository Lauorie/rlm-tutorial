import type { Iteration } from '../lib/types'

// 横向时间线：一张卡片 = RLM 主循环的一轮。点击切换查看。
// 这是理解"RLM 是一个循环"最直观的视图。
export function IterationTimeline({
  iterations,
  selected,
  onSelect,
}: {
  iterations: Iteration[]
  selected: number
  onSelect: (i: number) => void
}) {
  return (
    <div className="timeline">
      <div className="timeline-head muted">RLM 迭代时间线（共 {iterations.length} 轮）→</div>
      <div className="timeline-track">
        {iterations.map((it, i) => {
          const subCalls = it.code_blocks.reduce((n, b) => n + b.result.rlm_calls.length, 0)
          const hasError = it.code_blocks.some((b) => b.result.stderr.trim())
          const isFinal = it.final_answer !== null
          return (
            <button
              key={i}
              className={`tl-card ${i === selected ? 'active' : ''} ${
                isFinal ? 'final' : hasError ? 'err' : ''
              }`}
              onClick={() => onSelect(i)}
            >
              <div className="tl-num">{i + 1}</div>
              <div className="tl-badges">
                {isFinal && <span className="b b-green">FINAL</span>}
                {hasError && <span className="b b-red">ERR</span>}
                <span className="b">⟨⟩ {it.code_blocks.length}</span>
                {subCalls > 0 && <span className="b b-violet">◇ {subCalls}</span>}
              </div>
              <div className="tl-preview">
                {it.response.split('```')[0].trim().slice(0, 48) || '(直接写代码)'}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
