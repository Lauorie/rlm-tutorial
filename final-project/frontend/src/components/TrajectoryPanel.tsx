import type { Iteration, Message } from '../lib/types'

// 左侧：这一轮的对话历史（system / user / assistant）。
// 展示 RLM 不只是"跑代码"，而是模型在和环境多轮对话。
const ROLE_META: Record<string, { icon: string; label: string; cls: string }> = {
  system: { icon: '⚙', label: 'System（系统提示）', cls: 'role-system' },
  user: { icon: '👤', label: 'User（环境/轮次）', cls: 'role-user' },
  assistant: { icon: '🤖', label: 'Assistant（模型）', cls: 'role-assistant' },
}

function truncate(s: string, n = 1800) {
  return s.length > n ? s.slice(0, n) + `\n… [省略 ${s.length - n} 字]` : s
}

export function TrajectoryPanel({
  iteration,
  index,
  total,
}: {
  iteration: Iteration
  index: number
  total: number
}) {
  // 只展示最后几条消息，避免 system+长历史刷屏；重点是本轮的 user 提示 + 模型响应
  const msgs = iteration.prompt
  return (
    <div className="panel">
      <div className="panel-head">
        <span className="panel-title">💬 对话历史</span>
        <span className="muted">
          第 {index + 1} / {total} 轮
        </span>
      </div>
      <div className="panel-body">
        {msgs.map((m: Message, i: number) => {
          const meta = ROLE_META[m.role] ?? ROLE_META.user
          // system 提示很长，默认折叠成一行说明
          const isSystem = m.role === 'system'
          return (
            <div key={i} className={`msg ${meta.cls}`}>
              <div className="msg-head">
                <span>{meta.icon}</span>
                <span>{meta.label}</span>
              </div>
              <pre className="msg-body">
                {isSystem ? '（系统提示词：教模型如何当 RLM，已折叠）' : truncate(m.content)}
              </pre>
            </div>
          )
        })}
        <div className="msg role-assistant current">
          <div className="msg-head">
            <span>🤖</span>
            <span>本轮模型响应</span>
          </div>
          <pre className="msg-body">{truncate(iteration.response)}</pre>
        </div>
        {iteration.final_answer !== null && (
          <div className="final-answer">✓ 本轮交卷：{iteration.final_answer}</div>
        )}
      </div>
    </div>
  )
}
