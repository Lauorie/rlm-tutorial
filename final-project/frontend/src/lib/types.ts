// 这些类型刻意和后端 mini_rlm/types.py 的 to_dict() 输出一一对应。
// 后端吐 JSONL，前端读进来就是这套结构 —— 数据契约必须严格一致。

export interface Message {
  role: 'system' | 'user' | 'assistant'
  content: string
}

// 递归子调用：注意它本身又是一棵迭代树（这正是"递归"在数据上的体现）
export interface SubCall {
  response: string
  root_model: string
  depth: number
  iterations: Iteration[]
  usage: Usage
  execution_time: number
  stopped_reason: string // "leaf_llm"（叶子，无子迭代）| "final_answer"（完整子 RLM）
}

export interface Usage {
  total_calls: number
  input_tokens: number
  output_tokens: number
}

export interface REPLResult {
  stdout: string
  stderr: string
  locals: Record<string, string>
  execution_time: number
  rlm_calls: SubCall[]
  final_answer: string | null
}

export interface CodeBlock {
  code: string
  result: REPLResult
}

export interface Iteration {
  iteration: number
  prompt: Message[]
  response: string
  code_blocks: CodeBlock[]
  final_answer: string | null
  iteration_time: number
}

export interface TrajectoryMetadata {
  type: 'metadata'
  root_model: string
  max_depth: number
  max_iterations: number
  stopped_reason: string
  final_answer: string
  total_iterations: number
  total_code_blocks: number
  total_sub_calls: number
  total_execution_time: number
  usage: Usage
}

export interface Trajectory {
  metadata: TrajectoryMetadata
  iterations: Iteration[]
}

// 把后端的 JSONL（逐行）解析成一个 Trajectory 对象。
// 第一行是 metadata，其余每行是一个 iteration。
export function parseJsonl(text: string): Trajectory {
  const lines = text.trim().split('\n').filter((l) => l.trim())
  let metadata: TrajectoryMetadata | null = null
  const iterations: Iteration[] = []
  for (const line of lines) {
    const obj = JSON.parse(line)
    if (obj.type === 'metadata') metadata = obj
    else iterations.push(obj)
  }
  if (!metadata) throw new Error('轨迹缺少 metadata 行')
  return { metadata, iterations }
}
