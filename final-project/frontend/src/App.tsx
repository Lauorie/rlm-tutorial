import { useMemo, useState } from 'react'
import { SAMPLES } from './samples'
import { parseJsonl, type Trajectory } from './lib/types'
import { runRlm } from './lib/api'
import { IterationTimeline } from './components/IterationTimeline'
import { TrajectoryPanel } from './components/TrajectoryPanel'
import { ExecutionPanel } from './components/ExecutionPanel'
import { StatCards } from './components/StatCards'

export default function App() {
  const [trajectory, setTrajectory] = useState<Trajectory>(SAMPLES[0].trajectory)
  const [sampleId, setSampleId] = useState<string>(SAMPLES[0].id)
  const [selected, setSelected] = useState(0)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const current = trajectory.iterations[selected]

  function loadSample(id: string) {
    const s = SAMPLES.find((x) => x.id === id)!
    setTrajectory(s.trajectory)
    setSampleId(id)
    setSelected(0)
    setError(null)
  }

  function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        setTrajectory(parseJsonl(String(reader.result)))
        setSampleId('upload')
        setSelected(0)
        setError(null)
      } catch (err) {
        setError('解析失败：' + (err as Error).message)
      }
    }
    reader.readAsText(file)
  }

  async function onRunLive() {
    setRunning(true)
    setError(null)
    try {
      const t = await runRlm({ scenario: sampleId === 'upload' ? 'find-secret' : sampleId })
      setTrajectory(t)
      setSelected(0)
    } catch (err) {
      setError('在线运行失败（不影响样例查看）：' + (err as Error).message)
    } finally {
      setRunning(false)
    }
  }

  const subtitle = useMemo(
    () => SAMPLES.find((s) => s.id === sampleId)?.desc ?? '已加载自定义轨迹',
    [sampleId],
  )

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◆</span>
          <div>
            <h1>mini-RLM 轨迹可视化器</h1>
            <p className="muted">{subtitle}</p>
          </div>
        </div>
        <div className="controls">
          <select value={sampleId} onChange={(e) => loadSample(e.target.value)}>
            {SAMPLES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
            {sampleId === 'upload' && <option value="upload">自定义上传</option>}
          </select>
          <label className="btn ghost">
            上传 .jsonl
            <input type="file" accept=".jsonl,.json" hidden onChange={onUpload} />
          </label>
          <button className="btn primary" onClick={onRunLive} disabled={running}>
            {running ? '运行中…' : '▶ 在线运行'}
          </button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="answer-row">
        <div className="answer-card">
          <span className="label">最终答案</span>
          <div className="answer-text">{trajectory.metadata.final_answer || '（无）'}</div>
          <span className={`pill ${trajectory.metadata.stopped_reason}`}>
            {trajectory.metadata.stopped_reason}
          </span>
        </div>
        <StatCards meta={trajectory.metadata} />
      </section>

      <IterationTimeline
        iterations={trajectory.iterations}
        selected={selected}
        onSelect={setSelected}
      />

      <main className="split">
        <TrajectoryPanel iteration={current} index={selected} total={trajectory.iterations.length} />
        <ExecutionPanel iteration={current} />
      </main>

      <footer className="foot muted">
        数据契约与后端 <code>mini_rlm/types.py</code> 严格一致 · 教学项目
      </footer>
    </div>
  )
}
