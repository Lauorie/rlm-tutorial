import type { SubCall } from '../lib/types'

// 递归地渲染子调用。叶子（leaf_llm）画成一个简单卡片；
// 完整子 RLM 则展开它自己的迭代，其中可能又有子调用 —— 于是 SubCallTree 调用自己。
// 这个组件本身就是"递归"的，刚好对应 RLM 的递归结构。
export function SubCallTree({ call, depth }: { call: SubCall; depth: number }) {
  const isLeaf = call.stopped_reason === 'leaf_llm'
  return (
    <div className="subcall" style={{ marginLeft: depth > 0 ? 12 : 0 }}>
      <div className="subcall-head">
        <span className={`b ${isLeaf ? 'b-amber' : 'b-violet'}`}>
          {isLeaf ? '叶子 LLM' : `子 RLM · depth ${call.depth}`}
        </span>
        <span className="muted">
          {call.usage.input_tokens}↓ {call.usage.output_tokens}↑ tok
        </span>
      </div>
      <div className="subcall-answer">→ {call.response}</div>

      {/* 完整子 RLM：展开它自己的迭代和更深一层的子调用（递归！） */}
      {!isLeaf &&
        call.iterations.map((it, i) => (
          <div key={i} className="subcall-iter">
            <div className="muted small">子轮 {i + 1}</div>
            {it.code_blocks.map((b, j) => (
              <div key={j}>
                <pre className="code small">{b.code}</pre>
                {b.result.rlm_calls.map((c, k) => (
                  <SubCallTree key={k} call={c} depth={depth + 1} />
                ))}
              </div>
            ))}
          </div>
        ))}
    </div>
  )
}
