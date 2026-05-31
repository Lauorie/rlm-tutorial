import type { Iteration } from '../lib/types'
import { SubCallTree } from './SubCallTree'

// 右侧：本轮执行的每个代码块 + 它的 stdout/stderr + 触发的子调用。
// 这是"模型写代码、环境执行、结果反馈"闭环的可视化。
export function ExecutionPanel({ iteration }: { iteration: Iteration }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <span className="panel-title">⟨⟩ 代码执行 &amp; 子调用</span>
        <span className="muted">{iteration.code_blocks.length} 个代码块</span>
      </div>
      <div className="panel-body">
        {iteration.code_blocks.length === 0 && (
          <div className="muted">本轮模型没有写代码块（纯思考）。</div>
        )}
        {iteration.code_blocks.map((block, i) => {
          const r = block.result
          const hasError = r.stderr.trim().length > 0
          return (
            <div key={i} className={`exec-block ${hasError ? 'has-error' : ''}`}>
              <div className="exec-head">
                <span className="b">代码块 #{i + 1}</span>
                <span className="muted">{r.execution_time.toFixed(4)}s</span>
                {hasError && <span className="b b-red">报错</span>}
              </div>

              <pre className="code">{block.code}</pre>

              {r.stdout.trim() && (
                <div className="out">
                  <div className="out-label">stdout</div>
                  <pre className="out-body">{r.stdout}</pre>
                </div>
              )}
              {hasError && (
                <div className="out err">
                  <div className="out-label">stderr</div>
                  <pre className="out-body">{r.stderr}</pre>
                </div>
              )}

              {r.rlm_calls.length > 0 && (
                <div className="subcalls">
                  <div className="out-label">
                    本块触发了 {r.rlm_calls.length} 次子调用（llm_query / rlm_query）
                  </div>
                  {r.rlm_calls.map((c, k) => (
                    <SubCallTree key={k} call={c} depth={0} />
                  ))}
                </div>
              )}

              {r.final_answer !== null && (
                <div className="final-answer">✓ 此块设置了 answer，循环将结束</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
