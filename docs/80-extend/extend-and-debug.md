# 扩展与调试清单

恭喜——读到这里，你已经从一句洞察（"prompt 即环境 + 递归"）一路走到了一个能跑、能看、能部署的 mini-RLM。这一章是收尾，干两件事：

1. **扩展方向**：mini_rlm 为了教学做了很多简化。这里列出五个最值得动手的扩展，每个都指明**改哪个文件、难点在哪**，让你有路可循。
2. **调试清单**：把全教程散落各处的"常见错误"汇总成一张表，配症状和定位方法，当工具书查。

## 先认清"简化在哪"

要扩展，先得知道为了教学砍掉了什么。下面这张对照表把 mini_rlm 和官方实现摆在一起——**每一行被简化的地方，下面就对应一个扩展方向**。换句话说，"扩展"做的事，本质是沿着这张表把某一格从左边补到右边。

| 维度 | mini_rlm（教学版） | 官方实现 | 对应扩展 |
| --- | --- | --- | --- |
| 历史管理 | 线性追加，不压缩 | 有 compaction | 扩展 1 |
| 模型接入 | 一个 OpenAI 兼容客户端 | 多 provider | 扩展 2 |
| 代码执行 | 进程内 `exec`，非沙箱 | local/docker/e2b/modal/... | 扩展 3 |
| 子调用回主进程 | 同进程闭包直接调 | 多线程 TCP socket（`LMHandler`） | 扩展 3 的连带 |
| 子调用并发 | 串行 | `ThreadPoolExecutor` 批量 | 扩展 4 |
| 模型本身 | 通用大模型 + prompt 引导 | 可微调原生 RLM（RLM-Qwen3） | 扩展 5 |

mini_rlm 的设计取舍在 [项目结构与设计取舍](/50-build-backend/structure) 讲过：它故意砍掉了官方实现里的 socket 服务器、多环境、并发等"工程重料"，只留核心思想。下面每个扩展，本质都是把砍掉的某一块加回来。

### 1. 加 compaction：压缩长历史

**问题**：`MiniRLM.completion` 的主循环里，每一轮都往 `history` 里追加模型响应和反馈。轮数一多（`max_iterations` 默认 12，调大后更甚），**对话历史本身会越来越长**——这有点讽刺：RLM 的卖点是不让 context 进窗口，但它自己的"思考历史"还是线性增长的。

**扩展**：当历史超过某个阈值时，把早期几轮**压缩成一段摘要**（甚至可以用一个 `llm_query` 来压），替换掉原始的逐轮记录。这就是官方说的 compaction。

- **改哪个文件**：`mini_rlm/rlm.py` 的 `completion` 主循环（`rlm.py:96` 的 `for i in range(...)`）。在 append 反馈后插一个"历史超长则压缩"的步骤。
- **难点**：压缩会丢信息——被压掉的中间变量描述、试错过程，模型后面可能还要用。怎么决定"压什么、留什么"是核心权衡。一个稳妥的起点：只压"叙述性文字"，保留所有 stdout 里的关键事实和已确认的中间结论。

### 2. 加多 provider：不止 OpenAI

**问题**：现在真实模式只有一个 `OpenAICompatClient`（`clients.py:50`），走 OpenAI SDK。虽然它能靠 `OPENAI_BASE_URL` 切兼容服务，但本质还是 OpenAI 协议。想接 Anthropic、本地 Ollama 原生协议就不行。

**扩展**：再写几个 `BaseLM` 子类（`clients.py:31` 的抽象基类已经把接口定死了：`completion(messages) -> (text, in_tok, out_tok)`），比如 `AnthropicClient`、`OllamaClient`。

- **改哪个文件**：`mini_rlm/clients.py`。新增子类，并在 `build_client`（`clients.py:137`）里按 `backend` 字段路由。
- **难点**：不同 provider 的消息格式、system prompt 位置、token 计数方式都不一样，要在子类里各自适配，但**对外吐出的三元组接口必须一致**——这正是 `BaseLM` 抽象的价值。`RLMConfig.backend` 字段就是为这个预留的开关。

### 3. 接真实沙箱：隔离 exec

**问题**：这是全项目最大的安全短板。`repl.py:140` 那一行：

```python
exec(code, self.ns, self.ns)  # noqa: S102 教学用途，非安全沙箱
```

模型生成的代码**直接在你的 Python 进程里执行**，能读写文件、发网络请求、`os.system(...)`。教学和本地玩没问题，但任何"让真实模型在服务器上跑代码"的场景，这都是高危。

**扩展**：把 `execute_code` 从"进程内 exec"换成"在隔离环境里执行"——Docker 容器、gVisor、或 e2b / modal / daytona 这类远程沙箱服务（官方就支持这一整排）。

- **改哪个文件**：`mini_rlm/repl.py` 的 `execute_code` / `_run_code`。抽出一个"执行后端"接口，本地 exec 是默认实现，沙箱是另一个实现。
- **难点**：一旦代码在隔离环境里跑，`llm_query` / `rlm_query` 就**回不到主进程**了——子调用需要回调主进程的 LM 客户端。这正是官方为什么搞了个 `LMHandler` 多线程 TCP socket 服务器（见 [三层架构鸟瞰](/30-source/architecture-overview)）：让沙箱里的代码能通过 socket 回主进程发 LM 请求。我们用闭包直接调是因为同进程；隔离后这个简化就不成立了，这是这个扩展最硬的骨头。

### 4. 并发子调用

**问题**：`recursive-summary` 场景里，父 RLM 对每个章节 `rlm_query` 是**串行**的——一个章节总结完才轮到下一个。章节多时很慢。

**扩展**：当模型在一个循环里发出多个独立 `rlm_query`，把它们**并发**跑。官方在 `local_repl.py` 里就是用 `ThreadPoolExecutor` 批量执行的。

- **改哪个文件**：`mini_rlm/repl.py` 的 `_rlm_query` / `_spawn_subcall` 路径，引入线程池批量调度。
- **难点**：① 每个子调用是独立的 `MiniRLM` 实例，本身没问题；但若它们共享可变状态（比如同一个 `MockLM` 的 `responses` 列表，靠顺序取台词）就会**线程不安全**——并发下取台词的顺序乱掉，mock 场景直接演错。真实模式没这个问题，但要注意 API 限速。② 轨迹日志的顺序也要处理好，否则可视化器画出来的递归树会错乱。

### 5. 训练原生 RLM：RLM-Qwen3 的思路

**问题**：到目前为止，RLM 的"会写代码、知道何时该递归、何时该交卷"全靠 **prompt 引导一个通用大模型**。通用模型并不是为这套交互范式训练的，行为不够稳。

**扩展（思路简述，不在本项目代码内）**：把 RLM 跑出来的**成功轨迹**当训练数据，去微调一个模型，让它**原生**就擅长这套"peek / 切分 / llm_query / rlm_query / answer"的交互。论文里的 RLM-Qwen3-8B 就是这么做的：用 1000 条轨迹微调，比 base 模型中位数 **+28%**。

- **数据从哪来**：正是 `TrajectoryLogger` 落的那些 JSONL 轨迹（[日志、护栏与测试](/50-build-backend/logging-and-tests)）。把"高质量、最终答对"的轨迹筛出来，整理成 SFT 样本。
- **难点**：轨迹筛选（怎么定义"好轨迹"）、把多轮 REPL 交互拍平成训练格式、以及训练后还要防止模型"忘了"通用能力。这是一条独立的研究线，但起点就是你手里这个 logger 产出的数据。

把五个扩展按"难度 / 收益"摆一起，方便你挑：

| 扩展 | 主要改动文件 | 难度 | 收益 |
| --- | --- | --- | --- |
| compaction 压缩历史 | `rlm.py`（主循环） | 中 | 支持更多轮、更省 token |
| 多 provider | `clients.py` | 低 | 接入任意模型 |
| 隔离沙箱 exec | `repl.py`（+ 回调机制） | 高 | 安全，能上生产 |
| 并发子调用 | `repl.py` | 中 | 递归任务大提速 |
| 训练原生 RLM | （新流程，用 logger 数据） | 高 | 行为更稳，性能 +28% |

## RLM 调试清单

下面这张表汇总了全教程出现过的典型故障。RLM 的调试有个特点：**很多问题不是程序报错，而是"模型行为不对"**——循环没崩，但答案是错的或永远不交卷。所以症状栏特意区分"报错型"和"行为型"。

| # | 症状 | 类型 | 根因 | 怎么定位 / 解决 |
| --- | --- | --- | --- | --- |
| 1 | 模型回复有文字但 REPL 啥也没执行 | 行为 | 模型没用 ` ```repl ` 围栏写代码（写成普通代码块或纯文字） | `find_code_blocks` 正则只认 ` ```repl `。看轨迹里这一轮的原始响应；强化 system prompt 要求用 `repl` 块 |
| 2 | 循环跑满 `max_iterations` 才停，`stopped_reason="max_iterations"` | 行为 | 模型一直没设 `answer['ready']=True`，不交卷 | 这是兜底（`rlm.py:119`），不是崩溃。看模型是不是在反复试错/绕圈；prompt 里强调"拿到答案就立刻交卷" |
| 3 | 递归场景轨迹错乱，子调用对不上 | 行为 | mock 剧本里 `responses` 顺序 ≠ 真实调用顺序 | 父子共享一个 `MockLM` 按顺序取台词。对照 `scenarios.py` 把子调用台词穿插到正确位置（见 [在线 Demo](/70-run-deploy/online-demo)） |
| 4 | 模型看到的 stdout 被截断、丢了关键信息 | 行为 | stdout 超过 `stdout_truncate_chars`（默认 4000） | `_truncate`（`parsing.py:80`）会截。让模型别一次 `print` 一大坨，改成分页/只打摘要；或按需调大阈值 |
| 5 | 真实模式跑代码删了文件 / 发了网络请求 | 安全 | `exec` 不是沙箱（`repl.py:140`） | 本地有此风险意识；要上线请走"扩展 3"的隔离沙箱 |
| 6 | `rlm_query` 没递归，行为和 `llm_query` 一样 | 行为 | 已到 `max_depth`，`subcall_fn=None`，`rlm_query` 退化 | `_make_repl` 只在 `depth+1 < max_depth` 时给 `subcall_fn`（`rlm.py:162`）。想要递归就调大 `max_depth`（默认 2） |
| 7 | `ModuleNotFoundError: No module named 'mini_rlm'` | 报错 | venv 没激活，或没 `pip install -e .` | 见 [本地全链路](/70-run-deploy/run-local)：激活 venv、装包 |
| 8 | `ModuleNotFoundError: No module named 'openai'` | 报错 | 跑 `--real`/`use_real` 但没装 openai | `uv pip install -e ".[openai]"`；mock 模式不需要 |
| 9 | 线上 `/api/rlm` 500，`No module named 'scenarios'/'mini_rlm'` | 报错 | 函数没打包后端代码 | `vercel.json` 配 `includeFiles: "final-project/backend/**"`（见 [部署到 Vercel](/70-run-deploy/deploy-vercel)） |
| 10 | 在线运行超时 / 504 | 报错 | 开了 `use_real` 撞 Serverless 时限（约 10s） | 改回默认 mock，或换快模型/升级计划 |
| 11 | iframe 空白 | 行为 | `docs/public/demo` 没生成 | `npm run demo:build`；构建顺序 demo 先于 docs |
| 12 | 可视化器资源 404 / 样式错乱 | 行为 | 前端 `base` 不是相对路径 | 保持 `vite.config.ts` 的 `base: './'` |
| 13 | 端口被占（Address already in use） | 报错 | 8000 / 5173 被旧进程占 | `lsof -i :8000` 找进程 kill，或换端口（同步改 vite 代理） |

::: tip 调"行为型"问题的万能第一步：读轨迹
报错型问题有堆栈好查；行为型问题（1、2、3、4、6）最有效的办法是**打开轨迹**——无论是 `TrajectoryLogger` 落的 JSONL，还是可视化器里逐轮看。RLM 的每一步决策（写了什么代码、看到什么 stdout、为什么没交卷）都在轨迹里。先看模型这一轮"实际做了什么"，再倒推哪里出了偏差，比盯着代码瞎猜快得多。
:::

## 一次完整的"行为型"排查示范

清单是查表用的，但真正排查时怎么走？拿清单里 **#2（跑满 max_iterations 不交卷）** 走一遍，体会"读轨迹倒推"的节奏：

1. **现象**：调用 `completion` 拿到的 `RLMResult.stopped_reason` 是 `"max_iterations"`，答案是空或半成品。
2. **第一判断**：这不是崩溃。`rlm.py:119` 那行 `result.stopped_reason = "max_iterations"` 是循环正常跑满后的**兜底**——说明模型 12 轮里**始终没设** `answer['ready']=True`。
3. **打开轨迹**：看 `TrajectoryLogger` 落的 JSONL（或可视化器逐轮翻）。重点看后几轮模型在干嘛。常见三种画面：
   - 模型在**反复试同一段代码**（比如正则老是不命中）→ 是任务本身没解决，不是不肯交卷。
   - 模型已经 `print` 出了答案，却**只在 stdout 里打印、没往 `answer` 里塞**→ 它"以为打印就算交卷"，是协议理解问题。
   - 模型每轮都在"再确认一下"→ 过度谨慎。
4. **对症**：
   - 第一种：改 prompt 给更明确的解题提示，或本就该报"未找到"。
   - 第二种（最常见）：强化 system / turn prompt——明说"打印不等于交卷，必须 `answer['content']=...; answer['ready']=True`"。
   - 第三种：prompt 里加"一旦得到答案立即交卷，不要反复确认"。

注意这三种的修法**都落在 `prompts.py`**，而不是 `rlm.py`。这印证了一条经验：**行为型问题的修复点，往往在 prompt，不在循环代码**。循环代码只负责兜底防死循环（这它已经做到了）。

## 收尾

到这里，整套《RLM 从零到一》就走完了：从"为什么不能把长 prompt 塞进窗口"的洞察，到论文算法、官方源码、五个渐进 Demo，再到亲手实现后端、前端、本地跑通、公网部署，最后是这份扩展与调试清单。

你手里这个 mini-RLM 虽小，但**核心思想一个没缺**：prompt 即环境、用代码符号化操作、递归子调用。它和官方实现的差距，基本就是上面五个扩展——而每一个，你现在都知道该从哪个文件、哪一行下手。

去把它跑起来，改改看。最好的理解，永远来自亲手把它弄坏再修好。

## 小练习

1. 你想做"扩展 4 并发子调用"，先在 **mock 场景**里试。结果发现并发后 `recursive-summary` 的轨迹彻底乱了，但同样的改动在真实模式下却基本正常。为什么？

::: details 参考思路
因为 mock 模式下父子**共享同一个 `MockLM`**，它靠"按顺序从 `responses` 列表取台词"工作。串行时取台词顺序是确定的；一旦并发，多个子调用同时来取，顺序就乱了，于是每个子 RLM 拿到的不是给它准备的台词——轨迹自然错乱。真实模式没有"按顺序取剧本"这回事，每个子调用独立请求模型，所以不受影响（但要注意 API 限速）。这说明：并发改造要么让每个子调用持有**独立**的 mock 实例，要么 mock 的取词逻辑得做成线程安全/按调用上下文路由。
:::

2. 调试清单里第 1 条（模型不写 `repl` 块）和第 2 条（不交卷）都属于"行为型"问题，循环没报错。如果只能加**一处**改动来同时缓解这两类问题，你会改哪里？

::: details 参考思路
改 **prompt**——具体是 `mini_rlm/prompts.py` 里的 system prompt / turn prompt。这两类问题本质都是"模型没按约定的交互协议行动"：没用 `repl` 围栏、没用 `answer['ready']=True` 交卷。最直接的杠杆是把协议在 prompt 里讲得更清楚、给正例、在每轮提示里复述关键约定（mini_rlm 的第 0 轮 turn prompt 就有"先 peek"的 safeguard 提醒，可以照此补强"必须用 repl 块""拿到答案立刻交卷"）。代码层面的兜底（max_iterations）只能防死循环，治不了根；根在引导模型行为，而那靠 prompt。
:::
