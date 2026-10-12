## 前言

分析对应本地源码版本 `0.80.6`，重点文件包括：

- `packages/agent/src/types.ts`
- `packages/agent/src/agent-loop.ts`
- `packages/agent/src/agent.ts`
- `packages/agent/src/harness/agent-harness.ts`
- `packages/agent/src/harness/session/*`
- `packages/agent/src/harness/compaction/*`
- `packages/ai/src/types.ts`

完整分析和 Python 实现已保存于：

- [pi Agent 架构分析](../python/mini-pi-agent-python/docs/pi-agent-architecture.md)
- [Python 实现教程](../python/mini-pi-agent-python/docs/build-mini-pi-agent.md)
- [完整 Python 项目](../python/mini-pi-agent-python)

# 一、pi mono Agent 的整体定位

pi Agent 并不是把所有 Agent 能力塞进一个巨大框架，而是采用分层设计：

```
packages/ai
    模型协议、Provider、流式响应、工具调用格式
          ↓
packages/agent Core
    Agent Loop、消息、状态、事件、工具执行、队列
          ↓
Agent Harness
    Session、Hooks、资源、压缩、分支、持久化
          ↓
Coding Agent / Application
    文件操作、Shell、技能、Prompt、交互界面
```

三层分别回答不同问题：

```
pi-ai：
如何调用不同大模型？

Agent Core：
如何围绕模型响应执行 Agent 循环？

Agent Harness：
如何把一次性 Agent Loop 变成可持久化、可扩展的应用运行环境？
```

其核心架构思想是：

> 用一个轻量、无状态的 Agent Loop 作为执行内核，再由有状态 Agent 和 Harness 逐层补充状态、队列、会话、压缩和持久化能力。

# 二、pi Agent 的主要架构组成

## 1. pi-ai：模型与 Provider 层

`packages/agent` 不直接调用 OpenAI、Anthropic 或 Google SDK，而是依赖 `packages/ai`。

它主要提供：

- 统一 `Model` 类型
- 统一 `Message` 类型
- 统一 Tool Schema
- Provider 流式响应
- AssistantMessage 流事件
- Thinking/Reasoning 表达
- Token Usage
- ToolCall
- Provider 错误转换
- 模型注册和能力描述

简化后相当于：

```typescript
interface Model {
  provider: string;
  id: string;
  api: string;
  contextWindow: number;
  maxTokens: number;
}

interface StreamFn {
  (
    model: Model,
    context: LLMContext,
    options: StreamOptions,
  ): AssistantMessageEventStream;
}
```

Agent Core 只调用统一流接口：

```
Agent Loop
    ↓
StreamFn
    ↓
pi-ai Provider Adapter
    ↓
OpenAI / Anthropic / Google / OpenRouter
```

这意味着 Agent Loop 中不需要出现：

```
if (provider === "openai") {
  // ...
} else if (provider === "anthropic") {
  // ...
}
```

Provider 差异被限制在 `pi-ai`。

------

## 2. types.ts：Agent 的协议中心

`packages/agent/src/types.ts` 定义了整个运行时共享的核心协议。

主要类型包括：

```
AgentMessage
AgentContext
AgentState
AgentTool
AgentToolResult
AgentEvent
AgentLoopConfig
BeforeToolCall
AfterToolCall
ShouldStopAfterTurn
```

它不是一个普通的 DTO 文件，而是 Agent Core 的领域模型。

## 2.1 AgentMessage

pi 区分两类消息：

```
AgentMessage：Agent 应用内部使用
LLM Message：发送给模型
```

`AgentMessage` 可以包含：

- user
- assistant
- toolResult
- UI notification
- compaction 信息
- 应用自定义消息

概念代码：

```
export interface CustomAgentMessages {}

export type AgentMessage =
  | Message
  | CustomAgentMessages[keyof CustomAgentMessages];
```

应用可以通过 declaration merging 扩展：

```typescript
declare module "@earendil-works/pi-agent-core" {
  interface CustomAgentMessages {
    notification: {
      role: "notification";
      text: string;
      timestamp: number;
    };
  }
}
```

关键价值是：

> Agent 的内部历史不必完全受 LLM 消息协议限制。

UI 消息、审计消息或状态消息可以进入 Agent Session，但不一定发送给模型。

------

## 2.2 AgentContext

Core 层的 Context 非常小：

```
interface AgentContext {
  systemPrompt: string;
  messages: AgentMessage[];
  tools: AgentTool[];
}
```

它刻意没有包含：

- 数据库连接
- Memory Service
- Provider SDK
- UI
- Session Storage
- 文件系统

这些能力由更高层提供。

------

## 2.3 AgentState

高层 `Agent` 对外暴露状态：

```typescript
interface AgentState {
  systemPrompt: string;
  model: Model<any>;
  thinkingLevel: ThinkingLevel;
  tools: AgentTool<any>[];
  messages: AgentMessage[];

  readonly isStreaming: boolean;
  readonly streamingMessage?: AgentMessage;
  readonly pendingToolCalls: ReadonlySet<string>;
  readonly errorMessage?: string;
}
```

状态分为两类。

持久业务状态：

```
systemPrompt
model
thinkingLevel
tools
messages
```

运行派生状态：

```
isStreaming
streamingMessage
pendingToolCalls
errorMessage
```

派生状态主要供 UI 使用，不会直接发送给模型。

------

## 3. Agent Loop：无状态执行内核

`agent-loop.ts` 是 pi Agent 最核心的文件。

它提供两类 API：

```
agentLoop(...)
agentLoopContinue(...)
```

以及基于 sink 的执行形式：

```
runAgentLoop(...)
runAgentLoopContinue(...)
```

其核心输入可以抽象为：

```typescript
interface AgentLoopConfig {
  model: Model;
  convertToLlm: (
    messages: AgentMessage[],
  ) => Message[] | Promise<Message[]>;

  transformContext?: (
    messages: AgentMessage[],
    signal?: AbortSignal,
  ) => Promise<AgentMessage[]>;

  getSteeringMessages?: () => Promise<AgentMessage[]>;
  getFollowUpMessages?: () => Promise<AgentMessage[]>;

  beforeToolCall?: BeforeToolCall;
  afterToolCall?: AfterToolCall;

  shouldStopAfterTurn?: ShouldStopAfterTurn;

  toolExecution?: "parallel" | "sequential";
}
```

注意：Agent Loop 不拥有 Session，也不拥有长期状态。

它接收 Context，修改消息数组，并输出事件。

------

# 三、Agent Loop 的完整执行过程

其控制流可以还原为：

```
agent_start
    ↓
读取待处理消息
    ↓
turn_start
    ↓
把用户/Steering 消息加入 Context
    ↓
transformContext
    ↓
convertToLlm
    ↓
调用模型
    ↓
流式产生 AssistantMessage
    ↓
模型是否调用 Tool？
    ├── 否 → turn_end
    │          ↓
    │       是否有 Follow-up？
    │          ├── 有 → 开始下一 Turn
    │          └── 无 → agent_end
    │
    └── 是 → 参数校验
               ↓
            beforeToolCall
               ↓
            执行 Tool
               ↓
            afterToolCall
               ↓
            生成 ToolResultMessage
               ↓
            turn_end
               ↓
            是否有 Steering？
               ├── 有 → 注入 Steering，下一 Turn
               └── 无 → 用 ToolResult 自动调用下一 Turn
```

可以浓缩为：

```typescript
while (!finished) {
  const messages = await prepareContext();

  const assistant = await callModel(messages);

  if (assistant.hasToolCalls()) {
    const toolResults =
      await executeToolBatch(assistant.toolCalls);

    context.messages.push(...toolResults);
    continue;
  }

  const steering = await getSteeringMessages();

  if (steering.length > 0) {
    context.messages.push(...steering);
    continue;
  }

  const followUp = await getFollowUpMessages();

  if (followUp.length > 0) {
    context.messages.push(...followUp);
    continue;
  }

  finished = true;
}
```

实际源码还处理了：

- Provider Stream
- Assistant 增量事件
- Tool 参数错误
- 工具不存在
- AbortSignal
- Tool 部分更新
- 批次 terminate
- 顺序与并行工具执行
- shouldStopAfterTurn

# 四、消息双阶段转换

这是 pi Agent 最值得借鉴的设计之一。

消息在发送给 LLM 前经过两个独立阶段：

```
AgentMessage[]
    ↓
transformContext()
    ↓
AgentMessage[]
    ↓
convertToLlm()
    ↓
LLM Message[]
```

## 1. transformContext

负责语义层面的上下文策略：

- 裁剪旧消息
- Context Compaction
- 插入摘要
- 插入外部数据
- 删除无关 ToolResult
- Token 预算控制

例如：

```
transformContext: async (messages, signal) => {
  return pruneOldMessages(messages);
}
```

它的输出仍然是 `AgentMessage[]`。

## 2. convertToLlm

负责模型协议转换：

- 过滤 UI-only 消息
- 转换自定义消息
- 转换 ToolResult
- 映射 role
- 生成模型可理解的消息

例如：

```
convertToLlm: (messages) => {
  return messages.flatMap((message) => {
    if (message.role === "notification") {
      return [];
    }

    return [message];
  });
}
```

这种分层避免了两类职责混在一起：

```
transformContext：模型应该看到哪些信息
convertToLlm：这些信息如何表达成模型协议
```

# 五、Turn 的设计语义

pi 中的一个 Turn 不是单纯的一次模型调用。

准确来说：

```
Turn =
一次 LLM 响应
+ 该响应产生的全部 Tool 调用
+ 全部 ToolResult
```

事件结构：

```
turn_start
    message_start assistant
    message_update
    message_end assistant

    tool_execution_start
    tool_execution_update
    tool_execution_end

    message_start toolResult
    message_end toolResult
turn_end
```

ToolResult 产生后，如果模型还需要总结，再开始下一个 Turn。

这使 `turn_end` 成为一个稳定边界：

- 当前模型响应完成
- 当前工具批次完成
- ToolResult 已生成
- 可以检查 Steering
- 可以创建 Checkpoint
- 可以执行 Context Compaction
- 可以安全停止

# 六、Tool 架构

## 1. AgentTool

概念接口：

```
interface AgentTool<TParameters, TDetails> {
  name: string;
  label: string;
  description: string;
  parameters: TSchema;

  executionMode?: "parallel" | "sequential";

  execute(
    toolCallId: string,
    parameters: TParameters,
    signal: AbortSignal,
    onUpdate?: (
      partial: AgentToolResult<TDetails>,
    ) => void,
  ): Promise<AgentToolResult<TDetails>>;
}
```

工具结果：

```
interface AgentToolResult<TDetails> {
  content: Content[];
  details: TDetails;

  // 只有整个工具批次全部 terminate，
  // Agent Loop 才真正停止自动后续模型调用。
  terminate?: boolean;
}
```

## 2. Tool 执行流水线

```
ToolCall
    ↓
查找 Tool
    ↓
解析参数
    ↓
Schema 校验
    ↓
tool_execution_start
    ↓
beforeToolCall
    ↓
执行 execute()
    ↓
接收 onUpdate()
    ↓
afterToolCall
    ↓
tool_execution_end
    ↓
ToolResultMessage
```

## 3. Tool 异常不会直接击穿 Agent

推荐 Tool 失败时抛异常：

```
execute: async () => {
  throw new Error("File not found");
}
```

Agent Loop 会把异常转换为：

```
{
  role: "toolResult",
  toolCallId: "...",
  isError: true,
  content: [...]
}
```

然后将错误反馈给模型。

这样模型可以：

- 修正参数
- 改用其他工具
- 向用户说明失败
- 停止执行

# 七、并行工具执行的双重顺序

pi 默认并行执行同一 AssistantMessage 中的多个工具。

但它区分两种顺序：

## 实际完成顺序

用于事件：

```
fast tool_execution_end
slow tool_execution_end
```

工具一完成，UI 就能立即显示。

## 模型来源顺序

用于持久化消息：

```
assistant.toolCalls[0] → toolResult[0]
assistant.toolCalls[1] → toolResult[1]
```

即使第二个工具先完成，最终 ToolResult 仍按模型原始调用顺序写入。

这样同时满足：

- UI 实时响应
- Transcript 确定性
- 模型上下文稳定
- 测试可重复

Python mini 版保留了这一设计：

```typescript
tasks = [
    asyncio.create_task(
        execute_one_tool(index, call)
    )
    for index, call in enumerate(calls)
]

# 完成事件按真实完成顺序产生。
completed = [
    await task
    for task in asyncio.as_completed(tasks)
]

# 写入消息前恢复模型原始调用顺序。
ordered = sorted(
    completed,
    key=lambda item: item.source_index,
)
```

# 八、批次串行升级

工具执行模式有两个来源：

```
Agent 全局配置
Tool 自身配置
```

如果全局是 parallel，但某个 Tool 指定：

```
executionMode: "sequential"
```

则当前整个批次都串行执行。

逻辑类似：

```
force_sequential = (
    config.tool_execution == "sequential"
    or any(
        tool.execution_mode == "sequential"
        for tool in current_batch
    )
)
```

这是因为 ToolCall 可能存在隐式依赖：

```
创建文件
→ 修改文件
→ 读取文件
```

如果其中一个要求顺序，仅串行执行该工具本身仍然无法保证批次语义，所以整个批次升级为串行。

# 九、beforeToolCall 和 afterToolCall

## beforeToolCall

执行位置：

```
参数解析和校验之后
Tool 真正执行之前
```

可以用于：

- 权限检查
- 人工审批
- 路径限制
- 命令安全检查
- 参数标准化
- 禁止危险 Tool

概念代码：

```typescript
beforeToolCall: async ({ toolCall, args }) => {
  if (toolCall.name === "bash") {
    return {
      block: true,
      reason: "bash is disabled",
    };
  }
}
```

## afterToolCall

执行位置：

```
Tool 已完成
tool_execution_end 事件之前
ToolResultMessage 创建之前
```

可以：

- 修改结果
- 增加审计字段
- 截断输出
- 脱敏
- 设置 terminate

```typescript
afterToolCall: async ({
  toolCall,
  result,
  isError,
}) => {
  if (!isError) {
    return {
      details: {
        ...result.details,
        audited: true,
      },
    };
  }
}
```

# 十、terminate 的全批语义

假设模型同时调用两个工具：

```
Tool A → terminate: true
Tool B → terminate: false
```

Agent 不会提前结束。

只有：

```
Tool A → terminate: true
Tool B → terminate: true
```

才停止自动后续模型调用。

源码语义可以表示为：

```typescript
function shouldTerminateToolBatch(results) {
  return (
    results.length > 0 &&
    results.every(
      result => result.terminate === true
    )
  );
}
```

这样可以避免一个局部工具意外吞掉整个批次的后续总结。

# 十一、Steering 和 Follow-up

pi 为运行期间的用户消息设计了两条队列。

## 1. Steering

Steering 用于改变 Agent 当前方向：

```
agent.steer({
  role: "user",
  content: "停止原计划，改为先检查配置文件。",
});
```

但它不会粗暴取消已经执行中的工具。

执行顺序是：

```
当前 Assistant 完成
→ 当前工具批次全部完成
→ turn_end
→ 读取 Steering
→ 将 Steering 加入 Context
→ 开始下一 Turn
```

这种设计承认一个重要现实：

> 外部副作用不一定能安全取消，Steering 应在清晰的 Turn 边界改变下一步，而不是假装撤销已经发生的操作。

## 2. Follow-up

Follow-up 是在 Agent 原本准备结束时继续追加工作：

```
agent.followUp({
  role: "user",
  content: "再总结一下刚才的结果。",
});
```

检查顺序：

```
Tool 后续
→ Steering
→ Follow-up
→ Agent 结束
```

## 3. QueueMode

两种队列都支持：

```
one-at-a-time
all
```

`one-at-a-time` 每次只取一条，便于逐条处理。

`all` 一次取出全部，适合批量合并用户输入。

# 十二、高层 Agent 类

低层 Agent Loop 是无状态执行函数，高层 `Agent` 类负责状态和生命周期。

它主要包含：

```
AgentState
Active Run
Subscriber
AbortController
Steering Queue
Follow-up Queue
AgentLoopConfig
```

主要 API：

```typescript
class Agent {
  prompt(input): Promise<void>;
  continue(): Promise<void>;

  steer(message): void;
  followUp(message): void;

  abort(): void;
  waitForIdle(): Promise<void>;

  subscribe(listener): Unsubscribe;

  reset(): void;
}
```

## Subscriber Barrier

这是一个细节但很关键。

高层 Agent 按注册顺序等待 subscriber：

```
for (const listener of listeners) {
  await listener(event, signal);
}
```

因此：

```
message_end
→ AgentState 加入 AssistantMessage
→ 等待 Session Subscriber 完成写入
→ 才开始 beforeToolCall
```

这让状态持久化可以成为工具执行之前的屏障。

低层事件流则主要是 observational，不保证异步消费者完成后生产者才进入下一阶段。

# 十三、Agent Harness

Agent Harness 位于 Agent Core 之上。

它负责把轻量 Agent Loop 变成一个更完整的应用运行环境。

主要组成：

```
AgentHarness
Session
SessionStorage
SessionRepo
ExecutionEnv
Resources
Hooks
Compaction
Branch Summarization
Prompt Templates
Skills
Observability
```

## 1. Harness Phase

Harness 维护显式 phase：

```
type AgentHarnessPhase =
  | "idle"
  | "turn"
  | "compaction"
  | "branch_summary"
  | "retry";
```

这样可以阻止非法并发操作：

```
运行 Turn 时不能 compact
compact 时不能 prompt
idle 时不能 steer
```

## 2. Turn Resource Snapshot

每个 Turn 开始时，Harness 获取资源快照：

```
Model
Tools
Skills
Prompt Templates
Stream Options
System Prompt
```

Turn 内保持稳定，Turn 之间允许更新。

这避免运行途中工具集合、模型配置或系统提示词突然变化。

## 3. 动态 System Prompt

Harness 支持函数式 System Prompt：

```
systemPrompt: async ({
  session,
  resources,
  model,
}) => {
  return buildSystemPrompt(...);
}
```

它可以根据：

- 当前 Session
- 工作目录
- 可用 Tools
- Skills
- 模型能力

动态生成 Prompt。

# 十四、树形 Session

Harness 的 Session 不是一个线性消息数组，而是追加式树。

Entry 类型包括：

```
message
model_change
thinking_level_change
active_tools_change
compaction
branch_summary
custom
custom_message
label
session_info
```

概念接口：

```
interface SessionTreeEntryBase {
  id: string;
  parentId?: string;
  timestamp: number;
  type: string;
}
```

当前 Session 通过 leaf 指向活跃分支：

```
root
 ├── message A
 │    ├── message B
 │    │    └── message C   ← 当前 leaf
 │    └── message D
 └── message E
```

这样可以：

- 回到历史节点
- 从旧节点继续
- 创建分支
- 为废弃分支生成摘要
- 保存模型和工具配置变化
- 重建任意时刻的上下文

# 十五、Session 写屏障

Harness 不一定在每个事件到达时立即写存储，而是维护：

```
pendingSessionWrites: PendingSessionWrite[]
```

在安全边界统一 flush：

```
Assistant message_end
→ pending write
→ flush session
→ Tool preflight
```

这样减少了：

- 状态与外部操作顺序不一致
- Assistant 已调用 Tool 但请求消息尚未落盘
- 崩溃后无法恢复 Tool 来源

# 十六、Context Compaction

Compaction 不在 Core，而在 Harness。

大致流程：

```
读取当前分支
→ 判断哪些消息需要压缩
→ 选择保留消息
→ 调用模型生成摘要
→ 写入 CompactionEntry
→ 后续 Context 使用摘要 + 保留消息
```

这解释了 Core 为什么只提供：

```
transformContext(messages)
```

Core 提供扩展缝隙，Harness 实现具体压缩策略。

# 十七、Harness Hooks

Harness Hooks 同时支持 Observer 和 Interceptor。

可观察事件：

```
queue_update
save_point
abort
settled
model_update
tools_update
resources_update
```

可返回修改结果的 Hook：

```
before_agent_start
context
before_provider_request
before_provider_payload
tool_call
tool_result
session_before_compact
session_before_tree
```

例如：

```
context hook
→ 替换发给模型的 Context

tool_call hook
→ 阻止调用

tool_result hook
→ 修改 ToolResult

before_provider_payload
→ 修改最终 Provider Payload
```

这是一种典型的洋葱式扩展架构。

# 十八、pi Agent 的关键设计总结

最值得借鉴的设计有：

1. Provider 层与 Agent Runtime 分离。
2. Agent Loop 保持轻量、无状态。
3. 高层 Agent 只负责状态、队列和订阅屏障。
4. AgentMessage 与 LLM Message 分离。
5. Context Transform 与协议转换分离。
6. 事件协议贯穿 UI、状态、持久化和可观测性。
7. Turn 是模型响应与完整工具批次的边界。
8. 工具并行执行，但 Transcript 顺序保持确定。
9. 工具错误转成 Observation，而不是直接击穿循环。
10. Steering 和 Follow-up 使用不同优先级队列。
11. terminate 使用全批一致规则。
12. Harness 使用资源快照保证 Turn 内一致性。
13. Session 使用追加式树支持分支、回溯和压缩。
14. Compaction 属于上层 Context 策略，不污染 Agent Core。
15. Hooks 既可以观察，也可以修改执行。

------

# 十九、Python mini 版整体架构

Python mini 版位于：

[mini-pi-agent-python](../python/mini-pi-agent-python)

目录如下：

```
mini-pi-agent-python/
├── pyproject.toml
├── README.md
├── mini_pi_agent/
│   ├── __init__.py
│   ├── types.py
│   ├── model.py
│   ├── tools.py
│   ├── loop.py
│   ├── agent.py
│   ├── session.py
│   └── fake_model.py
├── examples/
│   ├── basic.py
│   └── tool_and_steering.py
├── tests/
│   ├── test_agent_loop.py
│   └── test_agent.py
└── docs/
    ├── pi-agent-architecture.md
    └── build-mini-pi-agent.md
```

运行关系：

```
Application
    ↓
Agent
    ↓
run_agent_loop()
    ↓
Model
    ↓
AssistantMessage
    ├── Final Text → 结束
    └── ToolCall
          ↓
       AgentTool
          ↓
       ToolResultMessage
          ↓
       再次调用 Model
```

# 二十、第一步：定义消息、状态和事件

关键文件：

[types.py](../python/mini-pi-agent-python/mini_pi_agent/types.py)

先定义文本块和工具调用：

```python
@dataclass(slots=True)
class TextBlock:
    """Assistant 输出中的普通文本块。"""

    text: str
    type: Literal["text"] = "text"


@dataclass(slots=True)
class ToolCall:
    """模型提出的结构化工具调用。

    id:
        关联之后的 ToolResultMessage。

    name:
        要调用的工具名称。

    arguments:
        已经解析后的参数对象。
    """

    id: str
    name: str
    arguments: dict[str, Any]
    type: Literal["tool_call"] = "tool_call"
```

AssistantMessage 同时允许文本和 ToolCall：

```python
AssistantBlock = TextBlock | ToolCall


@dataclass(slots=True)
class AssistantMessage:
    """一次模型调用完成后形成的 Assistant 消息。"""

    content: list[AssistantBlock] = field(
        default_factory=list
    )

    stop_reason: Literal[
        "stop",
        "tool_use",
        "error",
        "aborted",
    ] = "stop"

    error_message: str | None = None
    timestamp: int = field(default_factory=now_ms)
    role: Literal["assistant"] = "assistant"

    @property
    def text(self) -> str:
        """提取所有文本块。"""

        return "".join(
            block.text
            for block in self.content
            if isinstance(block, TextBlock)
        )

    @property
    def tool_calls(self) -> list[ToolCall]:
        """提取模型提出的所有工具调用。"""

        return [
            block
            for block in self.content
            if isinstance(block, ToolCall)
        ]
```

ToolResult 将执行结果与消息分开：

```python
@dataclass(slots=True)
class ToolResult:
    """工具函数返回的内部结果。

    terminate 只是 Runtime 提示，不直接成为 LLM 协议字段。
    """

    content: str
    details: dict[str, Any] = field(
        default_factory=dict
    )
    terminate: bool = False


@dataclass(slots=True)
class ToolResultMessage:
    """写入 Agent Transcript、发送给模型的工具结果。"""

    tool_call_id: str
    tool_name: str
    content: str
    is_error: bool = False
    details: dict[str, Any] = field(
        default_factory=dict
    )
    role: Literal["tool_result"] = "tool_result"
```

事件使用统一信封：

```python
@dataclass(slots=True)
class AgentEvent:
    """供 UI、状态同步和持久化共同消费的事件。"""

    type: Literal[
        "agent_start",
        "agent_end",
        "turn_start",
        "turn_end",
        "message_start",
        "message_update",
        "message_end",
        "tool_execution_start",
        "tool_execution_update",
        "tool_execution_end",
    ]

    data: dict[str, Any] = field(
        default_factory=dict
    )
```

AgentState 区分持久状态和派生状态：

```python
@dataclass(slots=True)
class AgentState:
    system_prompt: str
    model: Any
    tools: list[Any] = field(default_factory=list)
    messages: list[Any] = field(default_factory=list)

    # 以下字段主要用于运行时 UI。
    is_streaming: bool = False
    streaming_message: AssistantMessage | None = None
    pending_tool_calls: set[str] = field(
        default_factory=set
    )
    error_message: str | None = None
```

# 二十一、第二步：抽象 Model

关键文件：

[model.py](../python/mini-pi-agent-python/mini_pi_agent/model.py)

模型请求：

```python
@dataclass(slots=True)
class ModelRequest:
    system_prompt: str
    messages: list[LLMMessage]
    tools: list[dict[str, Any]]
```

统一模型流事件：

```
@dataclass(slots=True)
class ModelEvent:
    """最小模型事件。

    text_delta:
        模型输出的一段文本。

    message_end:
        完整 AssistantMessage。
    """

    type: str
    delta: str | None = None
    message: AssistantMessage | None = None
```

模型端口：

```
class Model(Protocol):
    async def stream(
        self,
        request: ModelRequest,
        signal: asyncio.Event,
    ) -> AsyncIterator[ModelEvent]:
        ...
```

Agent Loop 只依赖这个协议，不依赖 OpenAI SDK。

## OpenAI-compatible 适配器

```python
@dataclass(slots=True)
class OpenAICompatibleModel:
    """适配 Chat Completions 兼容服务。

    base_url 可以指向：
    - OpenAI
    - OpenRouter
    - vLLM
    - 其他 OpenAI-compatible 服务
    """

    model: str
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 60.0

    async def stream(
        self,
        request: ModelRequest,
        signal: asyncio.Event,
    ) -> AsyncIterator[ModelEvent]:
        if signal.is_set():
            raise asyncio.CancelledError()

        payload = {
            "model": self.model,
            "messages": (
                [{
                    "role": "system",
                    "content": request.system_prompt,
                }]
                if request.system_prompt
                else []
            ) + request.messages,
        }

        if request.tools:
            payload["tools"] = request.tools

        # urllib 是同步 API，放进线程避免阻塞事件循环。
        response = await asyncio.to_thread(
            self._post,
            payload,
        )

        message = parse_provider_response(response)

        if message.text:
            yield ModelEvent(
                type="text_delta",
                delta=message.text,
            )

        yield ModelEvent(
            type="message_end",
            message=message,
        )
```

# 二十二、第三步：实现 FakeModel

关键文件：

[fake_model.py](../python/mini-pi-agent-python/mini_pi_agent/fake_model.py)

不能只用真实模型测试 Agent Loop，因为真实模型输出不确定。

```python
@dataclass(slots=True)
class ScriptedModel:
    """每次调用取出一个预先写好的 AssistantMessage。"""

    responses: list[AssistantMessage]
    requests: list[ModelRequest] = field(
        default_factory=list
    )

    async def stream(
        self,
        request: ModelRequest,
        signal: asyncio.Event,
    ) -> AsyncIterator[ModelEvent]:
        if signal.is_set():
            raise asyncio.CancelledError()

        # 保存请求，测试可以检查模型究竟看到了什么。
        self.requests.append(request)

        if not self.responses:
            raise RuntimeError(
                "ScriptedModel has no response left"
            )

        message = self.responses.pop(0)

        # 逐字符产生 delta，验证流式状态更新。
        for char in message.text:
            if signal.is_set():
                raise asyncio.CancelledError()

            await asyncio.sleep(0)

            yield ModelEvent(
                type="text_delta",
                delta=char,
            )

        yield ModelEvent(
            type="message_end",
            message=message,
        )
```

测试时可以预先规定：

```python
model = ScriptedModel([
    AssistantMessage(
        content=[
            ToolCall(
                id="call-1",
                name="calculate",
                arguments={"a": 2, "b": 3},
            )
        ],
        stop_reason="tool_use",
    ),
    AssistantMessage(
        content=[
            TextBlock("计算结果是 5。")
        ]
    ),
])
```

第一次模型调用一定产生 ToolCall，第二次一定产生最终回答。

# 二十三、第四步：实现 AgentTool

关键文件：

[tools.py](../python/mini-pi-agent-python/mini_pi_agent/tools.py)

```python
@dataclass(slots=True)
class ToolExecutionContext:
    """工具执行期间可访问的运行信息。"""

    tool_call_id: str

    # asyncio.Event 表达取消信号。
    signal: asyncio.Event

    # 工具可以通过它产生部分进度。
    on_update: ToolUpdateCallback

    def raise_if_cancelled(self) -> None:
        if self.signal.is_set():
            raise asyncio.CancelledError(
                "agent run was aborted"
            )
```

Tool 定义：

```python
@dataclass(slots=True)
class AgentTool:
    name: str
    description: str
    parameters: dict[str, Any]
    execute: ToolExecutor

    label: str | None = None

    execution_mode: Literal[
        "parallel",
        "sequential",
    ] | None = None

    def validate(
        self,
        arguments: dict[str, Any],
    ) -> None:
        """教学版只验证 required。

        生产版本应接入完整 JSON Schema Validator。
        """

        required = self.parameters.get(
            "required",
            [],
        )

        missing = [
            name
            for name in required
            if name not in arguments
        ]

        if missing:
            raise ValueError(
                "missing required argument(s): "
                + ", ".join(missing)
            )
```

工具示例：

```python
async def calculate(context, arguments):
    # 先通知 UI 当前执行进度。
    await context.on_update(
        ToolResult("正在计算……")
    )

    context.raise_if_cancelled()

    result = arguments["a"] + arguments["b"]

    return ToolResult(
        content=str(result),
        details={
            "operation": "add",
            "a": arguments["a"],
            "b": arguments["b"],
        },
    )


tool = AgentTool(
    name="calculate",
    description="计算两个整数之和",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "integer"},
        },
        "required": ["a", "b"],
    },
    execute=calculate,
)
```

# 二十四、第五步：实现 Agent Loop

关键文件：

[loop.py](../python/mini-pi-agent-python/mini_pi_agent/loop.py)

配置接口：

```python
@dataclass(slots=True)
class AgentLoopConfig:
    model: Model

    # AgentMessage 转换为模型消息。
    convert_to_llm: ConvertToLlm

    # 可选的 Context 裁剪和压缩。
    transform_context: TransformContext | None = None

    # 两类运行中消息队列。
    get_steering_messages: MessageProvider | None = None
    get_follow_up_messages: MessageProvider | None = None

    # Tool 前后拦截器。
    before_tool_call: BeforeToolCall | None = None
    after_tool_call: AfterToolCall | None = None

    # 一个完整 Turn 后的停止策略。
    should_stop_after_turn: ShouldStopAfterTurn | None = None

    tool_execution: Literal[
        "parallel",
        "sequential",
    ] = "parallel"

    max_turns: int = 20
```

主循环核心：

```python
async def run_agent_loop(
    prompts,
    context,
    config,
    emit,
    signal,
):
    await emit(AgentEvent("agent_start"))

    new_messages = []
    pending_messages = list(prompts)
    turns = 0

    try:
        while True:
            if signal.is_set():
                raise asyncio.CancelledError()

            if turns >= config.max_turns:
                raise RuntimeError(
                    "maximum turns exceeded"
                )

            turns += 1

            await emit(
                AgentEvent(
                    "turn_start",
                    {"turn": turns},
                )
            )

            # 把本轮新消息加入 Context。
            for message in pending_messages:
                context.messages.append(message)
                new_messages.append(message)

                await emit(
                    AgentEvent(
                        "message_start",
                        {"message": message},
                    )
                )

                await emit(
                    AgentEvent(
                        "message_end",
                        {"message": message},
                    )
                )

            pending_messages = []

            # 调用模型并得到完整 AssistantMessage。
            assistant = await _stream_assistant_response(
                context,
                config,
                emit,
                signal,
            )

            context.messages.append(assistant)
            new_messages.append(assistant)

            tool_results = []
            terminate_batch = False

            if assistant.tool_calls:
                (
                    tool_results,
                    terminate_batch,
                ) = await _execute_tool_calls(
                    assistant.tool_calls,
                    context,
                    config,
                    emit,
                    signal,
                )

                context.messages.extend(tool_results)
                new_messages.extend(tool_results)

            await emit(
                AgentEvent(
                    "turn_end",
                    {
                        "message": assistant,
                        "tool_results": tool_results,
                    },
                )
            )

            # 应用可以在完整 Turn 边界优雅停止。
            if config.should_stop_after_turn:
                should_stop = await maybe_await(
                    config.should_stop_after_turn(...)
                )

                if should_stop:
                    break

            # 只有整个工具批次都 terminate 才结束。
            if terminate_batch:
                break

            steering = (
                await config.get_steering_messages()
                if config.get_steering_messages
                else []
            )

            if steering:
                pending_messages = steering
                continue

            # ToolResult 已加入上下文，自动让模型解释。
            if assistant.tool_calls:
                continue

            follow_up = (
                await config.get_follow_up_messages()
                if config.get_follow_up_messages
                else []
            )

            if follow_up:
                pending_messages = follow_up
                continue

            break

        return new_messages

    finally:
        # 即使异常或取消，也通知上层清理状态。
        await emit(
            AgentEvent(
                "agent_end",
                {"messages": new_messages},
            )
        )
```

# 二十五、第六步：流式处理 AssistantMessage

```python
async def _stream_assistant_response(
    context,
    config,
    emit,
    signal,
):
    messages = list(context.messages)

    # 第一阶段：上下文策略。
    if config.transform_context:
        messages = await config.transform_context(
            messages,
            signal,
        )

    # 第二阶段：转成 LLM 协议。
    llm_messages = await maybe_await(
        config.convert_to_llm(messages)
    )

    request = ModelRequest(
        system_prompt=context.system_prompt,
        messages=llm_messages,
        tools=[
            tool_to_openai_schema(tool)
            for tool in context.tools
        ],
    )

    partial = AssistantMessage(content=[])

    await emit(
        AgentEvent(
            "message_start",
            {"message": partial},
        )
    )

    streamed_text = ""
    final_message = None

    async for event in config.model.stream(
        request,
        signal,
    ):
        if event.type == "text_delta":
            streamed_text += event.delta

            partial = AssistantMessage(
                content=[
                    TextBlock(streamed_text)
                ]
            )

            await emit(
                AgentEvent(
                    "message_update",
                    {
                        "message": partial,
                        "delta": event.delta,
                    },
                )
            )

        elif event.type == "message_end":
            final_message = event.message

    await emit(
        AgentEvent(
            "message_end",
            {"message": final_message},
        )
    )

    return final_message
```

# 二十六、第七步：实现工具执行

先判断批次执行模式：

```python
force_sequential = (
    config.tool_execution == "sequential"
    or any(
        tools.get(call.name)
        and tools[call.name].execution_mode
            == "sequential"
        for call in calls
    )
)
```

并行执行：

```python
tasks = [
    asyncio.create_task(
        _execute_one_tool(
            source_index=index,
            call=call,
            tools=tools,
            context=context,
            config=config,
            emit=emit,
            signal=signal,
        )
    )
    for index, call in enumerate(calls)
]

# 按完成顺序 await，使结束事件及时发出。
finalized = [
    await task
    for task in asyncio.as_completed(tasks)
]
```

恢复源顺序：

```
ordered = sorted(
    finalized,
    key=lambda item: item.source_index,
)
```

生成 ToolResultMessage：

```python
messages = []

for item in ordered:
    message = ToolResultMessage(
        tool_call_id=item.call.id,
        tool_name=item.call.name,
        content=item.result.content,
        is_error=item.is_error,
        details=item.result.details,
    )

    messages.append(message)

    await emit(
        AgentEvent(
            "message_start",
            {"message": message},
        )
    )

    await emit(
        AgentEvent(
            "message_end",
            {"message": message},
        )
    )
```

计算批次终止：

```
terminate = (
    bool(ordered)
    and all(
        item.result.terminate
        for item in ordered
    )
)
```

# 二十七、第八步：实现单工具流水线

```python
async def _execute_one_tool(
    source_index,
    call,
    tools,
    context,
    config,
    emit,
    signal,
):
    await emit(
        AgentEvent(
            "tool_execution_start",
            {
                "tool_call_id": call.id,
                "tool_name": call.name,
                "args": call.arguments,
            },
        )
    )

    tool = tools.get(call.name)
    is_error = False

    try:
        if tool is None:
            raise ValueError(
                f"unknown tool: {call.name}"
            )

        # 参数校验在 Hook 前完成。
        tool.validate(call.arguments)

        if config.before_tool_call:
            decision = await config.before_tool_call(
                call,
                call.arguments,
                context,
            )

            if decision and decision.get("block"):
                raise PermissionError(
                    decision.get("reason")
                    or "tool call blocked"
                )

        async def on_update(partial):
            await emit(
                AgentEvent(
                    "tool_execution_update",
                    {
                        "tool_call_id": call.id,
                        "tool_name": call.name,
                        "partial_result": partial,
                    },
                )
            )

        execution_context = ToolExecutionContext(
            tool_call_id=call.id,
            signal=signal,
            on_update=on_update,
        )

        result = await tool.execute(
            execution_context,
            call.arguments,
        )

    except asyncio.CancelledError:
        # 取消不能转换为普通 Tool Error，
        # 必须继续传播给 Agent Runtime。
        raise

    except Exception as error:
        # 普通工具错误成为模型可观察结果。
        is_error = True

        result = ToolResult(
            content=str(error),
            details={
                "error_type":
                    type(error).__name__,
            },
        )

    if config.after_tool_call:
        patch = await config.after_tool_call(
            call,
            result,
            is_error,
            context,
        )

        if patch:
            result = replace(
                result,
                content=patch.get(
                    "content",
                    result.content,
                ),
                details=patch.get(
                    "details",
                    result.details,
                ),
                terminate=patch.get(
                    "terminate",
                    result.terminate,
                ),
            )

    await emit(
        AgentEvent(
            "tool_execution_end",
            {
                "tool_call_id": call.id,
                "tool_name": call.name,
                "result": result,
                "is_error": is_error,
            },
        )
    )

    return FinalizedToolCall(
        source_index=source_index,
        call=call,
        result=result,
        is_error=is_error,
    )
```

# 二十八、第九步：实现有状态 Agent

关键文件：

[agent.py](../python/mini-pi-agent-python/mini_pi_agent/agent.py)

配置：

```python
@dataclass(slots=True)
class AgentOptions:
    system_prompt: str
    model: Model

    tools: list[AgentTool] | None = None
    messages: list[Any] | None = None

    convert_to_llm: ConvertToLlm = (
        default_convert_to_llm
    )

    transform_context: TransformContext | None = None

    tool_execution: Literal[
        "parallel",
        "sequential",
    ] = "parallel"

    steering_mode: Literal[
        "all",
        "one-at-a-time",
    ] = "one-at-a-time"

    follow_up_mode: Literal[
        "all",
        "one-at-a-time",
    ] = "one-at-a-time"

    max_turns: int = 20

    before_tool_call: Any = None
    after_tool_call: Any = None
    should_stop_after_turn: Any = None

    session: MemorySession | None = None
```

Agent 构造：

```python
class Agent:
    def __init__(
        self,
        options: AgentOptions,
    ) -> None:
        self.state = AgentState(
            system_prompt=options.system_prompt,
            model=options.model,
            tools=list(options.tools or []),
            messages=list(options.messages or []),
        )

        self._steering = PendingMessageQueue(
            options.steering_mode
        )

        self._follow_up = PendingMessageQueue(
            options.follow_up_mode
        )

        self._subscribers = []
        self._abort_signal = asyncio.Event()
        self._active_task = None
```

# 二十九、第十步：事件驱动状态同步

```python
async def _emit(
    self,
    event: AgentEvent,
) -> None:
    # 先更新状态。
    self._apply_event(event)

    # 再依次等待订阅者。
    # 这样 subscriber 可以形成持久化屏障。
    for subscriber in list(
        self._subscribers
    ):
        result = subscriber(
            event,
            self._abort_signal,
        )

        if hasattr(result, "__await__"):
            await result
```

状态映射：

```python
def _apply_event(
    self,
    event: AgentEvent,
) -> None:
    data = event.data

    if event.type == "agent_start":
        self.state.is_streaming = True
        self.state.error_message = None

    elif (
        event.type == "message_start"
        and isinstance(
            data.get("message"),
            AssistantMessage,
        )
    ):
        self.state.streaming_message = (
            data["message"]
        )

    elif event.type == "message_update":
        self.state.streaming_message = (
            data["message"]
        )

    elif event.type == "message_end":
        self.state.streaming_message = None

    elif event.type == "tool_execution_start":
        self.state.pending_tool_calls.add(
            data["tool_call_id"]
        )

    elif event.type == "tool_execution_end":
        self.state.pending_tool_calls.discard(
            data["tool_call_id"]
        )

    elif event.type == "agent_end":
        self.state.streaming_message = None
        self.state.pending_tool_calls.clear()
        self.state.is_streaming = False
```

# 三十、第十一步：prompt、continue、abort

```python
async def prompt(
    self,
    prompt: str | Any,
) -> list[Any]:
    if self.state.is_streaming:
        raise RuntimeError(
            "agent is already running; "
            "use steer() or follow_up()"
        )

    if self.session and not self.state.messages:
        self.state.messages.extend(
            await self.session.load()
        )

    message = (
        UserMessage(prompt)
        if isinstance(prompt, str)
        else prompt
    )

    return await self._start(
        [message],
        continuing=False,
    )
```

Continue：

```python
async def continue_run(self) -> list[Any]:
    """从现有 user/tool_result 消息继续。

    不会插入新的用户消息，适合 Provider 错误后的重试。
    """

    if self.state.is_streaming:
        raise RuntimeError(
            "agent is already running"
        )

    return await self._start(
        [],
        continuing=True,
    )
```

取消：

```python
def abort(self) -> None:
    # 通知 Tool 和 Model。
    self._abort_signal.set()

    # 同时取消外层 asyncio Task。
    if self._active_task:
        self._active_task.cancel()
```

等待空闲：

```python
async def wait_for_idle(self) -> None:
    task = self._active_task

    if task:
        try:
            await task
        except asyncio.CancelledError:
            pass
```

# 三十一、第十二步：实现 Steering 和 Follow-up

队列：

```python
class PendingMessageQueue:
    def __init__(
        self,
        mode="one-at-a-time",
    ):
        self.mode = mode
        self._items = []

    def push(self, message):
        self._items.append(message)

    async def drain(self):
        if not self._items:
            return []

        if self.mode == "all":
            items = self._items
            self._items = []
            return items

        return [self._items.pop(0)]
```

Agent API：

```python
def steer(
    self,
    message: str | Any,
) -> None:
    if not self.state.is_streaming:
        raise RuntimeError(
            "cannot steer an idle agent"
        )

    self._steering.push(
        UserMessage(message)
        if isinstance(message, str)
        else message
    )


def follow_up(
    self,
    message: str | Any,
) -> None:
    if not self.state.is_streaming:
        raise RuntimeError(
            "cannot queue follow-up "
            "for an idle agent"
        )

    self._follow_up.push(
        UserMessage(message)
        if isinstance(message, str)
        else message
    )
```

# 三十二、第十三步：实现最小 Session

关键文件：

[session.py](../python/mini-pi-agent-python/mini_pi_agent/session.py)

```python
@dataclass(slots=True)
class MemorySession:
    """跨多次 prompt() 保存线性消息历史。

    它没有实现 pi Harness 的树形分支，
    但展示了 Session 不应进入 Agent Loop。
    """

    messages: list[Any] = field(
        default_factory=list
    )

    async def load(self) -> list[Any]:
        # 返回副本，避免外部直接修改 Session 内部数组。
        return list(self.messages)

    async def append(
        self,
        messages: list[Any],
    ) -> None:
        self.messages.extend(messages)

    async def clear(self) -> None:
        self.messages.clear()
```

Agent Loop 不知道 Session 的存在。

高层 Agent 在运行前加载、运行后写入：

```python
if self.session and not self.state.messages:
    self.state.messages.extend(
        await self.session.load()
    )

new_messages = await run_agent_loop(...)

if self.session:
    await self.session.append(new_messages)
```

# 三十三、完整使用示例

```python
import asyncio

from mini_pi_agent import (
    Agent,
    AgentOptions,
    AgentTool,
    AssistantMessage,
    ScriptedModel,
    TextBlock,
    ToolCall,
    ToolResult,
)


async def calculate(context, arguments):
    await context.on_update(
        ToolResult("正在计算……")
    )

    return ToolResult(
        content=str(
            arguments["a"] + arguments["b"]
        ),
        details={
            "operation": "add",
        },
    )


async def main():
    model = ScriptedModel([
        # 第一轮模型请求工具。
        AssistantMessage(
            content=[
                ToolCall(
                    id="call-1",
                    name="calculate",
                    arguments={
                        "a": 2,
                        "b": 3,
                    },
                )
            ],
            stop_reason="tool_use",
        ),

        # 第二轮模型解释 ToolResult。
        AssistantMessage(
            content=[
                TextBlock(
                    "计算结果是 5。"
                )
            ]
        ),
    ])

    tool = AgentTool(
        name="calculate",
        description="两个整数相加",
        parameters={
            "type": "object",
            "required": ["a", "b"],
        },
        execute=calculate,
    )

    agent = Agent(
        AgentOptions(
            system_prompt=(
                "使用工具完成计算。"
            ),
            model=model,
            tools=[tool],
        )
    )

    async def observe(
        event,
        _signal,
    ):
        if event.type == "message_update":
            print(
                event.data["delta"],
                end="",
                flush=True,
            )

        elif event.type == "tool_execution_start":
            print(
                "\n正在调用：",
                event.data["tool_name"],
            )

        elif event.type == "tool_execution_update":
            print(
                "\n工具进度：",
                event.data["partial_result"],
            )

    agent.subscribe(observe)

    await agent.prompt(
        "2 + 3 等于多少？"
    )


if __name__ == "__main__":
    asyncio.run(main())
```

# 三十四、测试覆盖了什么

当前测试结果：

```
7 passed
```

覆盖以下关键语义：

1. ToolCall 后自动进入下一轮模型调用。
2. Agent、Turn、Message、Tool 事件顺序。
3. Tool 进度事件。
4. mixed terminate 不提前结束。
5. before hook 可以阻止 Tool。
6. Tool 被阻止后生成错误 Observation。
7. AgentState 跟随事件更新。
8. subscriber 按顺序 await。
9. Follow-up 在正常完成点注入。
10. 并行 Tool 完成事件按真实时间排序。
11. ToolResult 按模型源顺序持久化。
12. Steering 优先于工具后的普通自动续跑。

运行：

```
cd D:\writer\my-prompt-skills\AI-Study\mini-pi-agent-python

python -m pytest -q
python examples\basic.py
python examples\tool_and_steering.py
```

# 三十五、mini 版与完整 pi 的边界

mini 版已经实现：

```
AgentMessage
LLM Message 转换
AgentState
AgentEvent
Agent Loop
Model Port
OpenAI-compatible Adapter
FakeModel
Tool
并行/串行 Tool Batch
Tool Update
before/after Hook
terminate
Steering
Follow-up
Abort
MemorySession
Subscriber Barrier
```

没有实现：

```
树形 Session
JSONL Storage
Session Repo
Branch Navigation
Branch Summary
Context Compaction
Skills
Prompt Templates
Durable Harness
完整 Provider SSE
完整 JSON Schema
Thinking Level
Provider Usage
Retry
Tracing
分布式恢复
Tool 权限与审批
外部副作用幂等
```

下一步若继续扩展，推荐顺序是：

```
完整 JSON Schema
→ Provider 真流式传输
→ SQLite/JSONL Session
→ 追加式 Session Tree
→ Context Compaction
→ Tool 权限和审批
→ Retry/Timeout
→ Tracing
→ Durable Runtime
```

最重要的是保持 pi 的分层原则：

> 不要把 Session、压缩、权限、Provider、UI 和持久化全部塞进 Agent Loop。Agent Loop 只负责从消息得到模型响应、执行工具、产生 Observation，并决定是否进入下一 Turn。