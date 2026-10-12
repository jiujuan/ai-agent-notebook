## 一、harness engineering 工程详细解释

**Harness Engineering（驾驭工程/马具工程）** 是 AI 大模型 Agent 应用开发中的一个重要新兴工程学科，尤其在 2026 年左右流行起来。它将 Agent 表述为 **Agent = Model（模型） + Harness（驾驭系统/外壳）**。

简单类比：**模型就像一匹强壮但容易跑偏的马**，Harness（马具，包括缰绳、鞍具等）则提供控制、方向、安全和执行框架，让马（模型）能可靠地完成实际任务。Harness 不是模型本身，而是围绕模型构建的全部“非模型”部分。

### 它用来解决哪些问题？
LLM 本身强大但存在固有局限，导致纯依赖 Prompt 或 Context Engineering 的 Agent 在生产环境中容易失败：

- **非确定性与幻觉**：模型输出不稳定，可能生成错误代码、错误决策或偏离目标。
- **缺乏持久状态和长时执行能力**：单次调用无法处理复杂、多步、长时间任务；上下文窗口有限，容易遗忘或溢出。
- **工具使用与现实世界交互不可靠**：不知道何时调用工具、如何验证结果、如何处理错误。
- **安全性与可控性不足**：可能执行破坏性操作、泄露数据，或在生产中失控。
- **可观测性、调试和迭代困难**：失败后难以追溯、修复和持续改进。
- **从原型到生产落地**：Demo 容易，长期可靠执行难；人类监督成本高。

**核心目标**：通过系统化“驾驭”，将模型的智能转化为**可靠、可重复、可审计的生产力**，让“人类 steering（引导），Agent execute（执行）”。它强调“每次 Agent 犯错，就工程化地永久修复该问题”。

### 它通过哪些方面来解决这些问题？
Harness Engineering 聚焦于构建**确定性的运行时层**（deterministic runtime layer），包括：

- **约束与前馈控制**（Guides/Feedforward）：系统提示、规则文件（如 CLAUDE.md、AGENTS.md）、权限控制、沙箱环境，提前引导行为、限制范围。
- **反馈循环与验证**（Feedback Loops）：执行结果观察、自我验证、错误恢复、评估机制（Evaluator）。
- **上下文与状态管理**：动态上下文组装、压缩（compaction）、内存系统（短期/长期）、状态持久化。
- **编排与执行逻辑**：Agent 循环（ReAct 等）、工具调用、子 Agent 协调、多步规划、生命周期钩子（hooks）。
- **可观测性与迭代**：日志、追踪、评估、持续优化 harness 本身。
- **基础设施**：文件系统、沙箱、浏览器等执行环境。

它超越 Prompt Engineering（说什么）和 Context Engineering（看什么），关注“**怎么干**”——整个系统架构和运行时保障。

### 开发一个具有 Harness Engineering 的 AI Agent 应用，应具备哪些组件？各组件功能是什么？
一个成熟的生产级 Agent Harness 通常包含以下核心组件（不同框架表述略有差异，但本质趋同，如 LangChain 的 Anatomy of an Agent Harness 等）。

1. **系统指令 / System Prompts / Guides（系统提示与规则文件）**  
   定义 Agent 的角色、目标、边界、行为规范（如优先级、风格、禁忌）。功能：提供一致的前馈引导，注入领域知识或公司规范，减少偏差。常包括 CLAUDE.md、AGENTS.md 等文件。

2. **工具与技能层 / Tools, Skills, MCPs**  
   外部接口（如 API 调用、代码执行、文件操作、搜索等），附带描述和 Schema。功能：让 Agent 能与现实世界交互；工具设计直接影响性能（少而精优于多而杂）。

3. **Agent 循环 / Orchestration Logic / Action Loop（核心执行循环）**  
   通常是 ReAct（Reason-Act）或其他循环：观察 → 规划 → 行动 → 反馈。功能：协调多步推理、工具调用、子 Agent 切换、模型路由；处理长时任务分解与执行。

4. **上下文管理与 Compaction（上下文工程子系统）**  
   动态检索、组装、压缩上下文（总结历史、优先级排序等）。功能：克服 token 限制，维持相关信息，防止上下文污染或遗忘。

5. **内存与状态管理 / Memory & State**  
   短期（会话内消息）、长期（跨会话数据库/向量存储）、工作目录状态等。功能：持久化进度、知识、历史决策，支持复杂项目。

6. **沙箱与安全层 / Sandbox, Guardrails, Permissions**  
   执行环境隔离、权限控制、输出验证、安全策略。功能：防止破坏性操作、数据泄露；授权特定行动。

7. **验证、评估与反馈循环 / Verification, Evaluator, Hooks**  
   自动测试、lint 检查、结果验证、中间件钩子（lifecycle hooks）。功能：自我纠正、质量把关；失败时触发恢复或人类介入。

8. **可观测性与日志 / Observability, Logging, Tracing**  
   记录所有提示、工具调用、决策、结果。功能：调试、审计、监控性能，支持事后分析和 harness 迭代。

9. **子 Agent 与多 Agent 协调 / Sub-agents, Orchestration**  
   专项子 Agent（如 Planner、Generator、Evaluator）。功能：分工协作，处理复杂任务（规划-生成-评估循环）。

10. **基础设施与持久化 / Bundled Infra & Persistence**  
    文件系统、浏览器、数据库等。功能：提供执行底座，支持长时间运行和状态恢复。

**额外生产特性**：评估框架（Evals）、持续改进机制（从失败中学习）、模型中立性（provider-neutral）等。

### 总结建议
开发时，先聚焦核心循环 + 工具 + 内存，再逐步添加 guardrails 和 observability。Harness 本身也是迭代 artifact——用 Agent 帮助改进 Harness。框架如 LangChain/LangGraph、Anthropic 的工具、OpenAI Agents SDK 等可加速构建，但生产级往往需要自定义大量工程化工作。

这个领域还在快速发展，强调“技能问题（skill issues）多于模型能力问题”，通过系统设计让当前模型发挥最大潜力。未来随着模型进步，部分 Harness 组件可能简化，但工程化思维会长期存在。

## 二、Agent Loop和Agent Runtime详细介绍

**Agent Loop（Agent 循环）** 和 **Agent Runtime（Agent 运行时）** 是 Harness Engineering 中最核心的动态执行部分。它们将静态的“模型 + Harness 配置”转变为能够自主、多步、可靠完成任务的运行系统。

### 1. 详细分析

**Agent Loop（核心执行循环）**：
- 经典实现是 **ReAct（Reasoning + Acting）**：**Thought（思考/规划） → Action（行动/工具调用） → Observation（观察结果） → Repeat**。
- 这是一个**反馈驱动的迭代循环**，模型在每次迭代中基于当前状态（上下文 + 历史 + 观察）决定下一步。
- 优点：灵活、能处理不确定性。
- 挑战：可能无限循环、幻觉累积、成本高、上下文膨胀。因此需要 Harness 层强力约束（如最大迭代次数、验证门、上下文压缩）。

**Agent Runtime（运行时）**：
- 提供**执行引擎**，负责循环的驱动、状态管理、错误恢复、持久化等基础设施。
- 它不是单纯的循环实现，而是**可靠的 orchestration 层**，类似操作系统的内核：调度、内存管理、中断处理、安全执行。
- 常见框架实现：LangGraph（图状态机）、自定义 Executor、Orchestrator-Worker 模式等。

二者关系：**Agent Loop 是业务逻辑心脏**，**Runtime 是承载它的可靠基础设施**。好的设计将 Loop 嵌入 Runtime 中，通过状态图（StateGraph）或事件驱动方式实现可控、可观测、可中断。

### 2. 如果让我架构设计：分层架构建议

我建议采用**分层 + 事件/状态驱动**架构，参考 LangGraph 的 StateGraph 思想，但更强调生产可靠性、生产级分离关注点（SoC）。整体分为 **5 层**（从下到上）：

#### **Layer 1: Infrastructure / Execution Foundation（基础设施层）**
- **组件**：
  - Sandboxed Executor（沙箱执行器）：代码解释器、API 调用容器、文件系统代理。
  - Tool Runtime Adapter：标准化工具调用（MCP、OpenAI Tools、自定义函数）。
  - Persistence Layer：数据库/向量存储/文件系统，用于状态快照。
- **功能**：
  - 安全隔离执行（防止恶意代码、资源超限）。
  - 工具调用标准化与重试。
  - 持久化状态（支持中断恢复、长时间运行）。
- **技术栈建议**：Docker/Kubernetes sandbox、Redis + Postgres + Vector DB（PGVector/Milvus）、LangChain Tool wrappers。

#### **Layer 2: State & Memory Management（状态与内存层）**
- **组件**：
  - Shared State Schema（共享状态结构）：TypedDict 或 Pydantic Model，包含 messages、tool_results、plan、metadata 等。
  - Short-term Memory（会话内存）：In-memory + 最近消息。
  - Long-term Memory（长期记忆）：向量检索 + Summary Agent。
  - Context Optimizer（上下文优化器）：Compaction、Prioritization、Summarization。
- **功能**：
  - 维护全局一致状态。
  - 动态管理上下文窗口（压缩历史、注入相关知识）。
  - 支持 checkpointing（快照）用于恢复和调试。
- **协作**：所有上层组件读写此 State；Runtime 在每个循环迭代后更新/持久化。

#### **Layer 3: Core Agent Loop Engine（核心循环引擎）**
- **组件**：
  - Loop Controller / Graph Runtime（循环控制器）：基于状态机或 while-loop。
  - LLM Caller（模型调用器）：带 retry、fallback、routing 的 wrapper。
  - Action Dispatcher（行动分发器）：解析工具调用、路由到 Layer 1 执行。
  - Observer / Feedback Handler：处理工具输出，生成 Observation。
- **功能**：
  - 驱动 ReAct 或扩展循环（Plan-Execute-Verify 等）。
  - 决策：是否继续循环、切换子 Agent、请求人类介入。
  - 集成中间件（middleware hooks）：pre/post LLM call、validation。
- **实现**：LangGraph StateGraph（节点：agent_node、tool_node；边：conditional edges）；或自定义 async event loop。

#### **Layer 4: Orchestration & Control Plane（编排与控制层）**
- **组件**：
  - Supervisor / Orchestrator：高层规划、子 Agent 管理、路由。
  - Guardrails & Policy Engine：权限检查、输出安全扫描、合规验证。
  - Evaluator / Verifier：质量评估（fact-check、code lint、task completion check）。
  - Lifecycle Hooks：on_start、on_tool_call、on_error、on_complete。
- **功能**：
  - 多 Agent 协调（hierarchical / swarm）。
  - 安全与质量门控。
  - 异常恢复策略（retry、fallback、human-in-loop）。
  - 动态规划调整。

#### **Layer 5: Observability & Management（可观测与管理层）**
- **组件**：
  - Tracing & Logging：OpenTelemetry、LangSmith 等，全链路追踪。
  - Metrics & Eval Dashboard：循环次数、token 消耗、成功率、瓶颈分析。
  - Human-in-the-Loop（HITL）接口：暂停、审批、反馈注入。
  - Self-Improvement Hooks：失败分析、harness 自动优化。
- **功能**：
  - 生产监控、调试、审计。
  - 支持 A/B 测试不同 Loop 策略。
  - 闭环学习（从运行数据改进 prompts/rules）。

### 3. 组件之间如何协作？

采用**事件驱动 + 共享状态**模式（推荐 StateGraph 或类似）：

1. **启动**：上层应用传入初始 State（goal + input）→ Layer 5 记录 → Layer 4 Orchestrator 初始化计划 → Layer 2 初始化内存。
2. **循环迭代**（核心流程）：
   - Layer 3 Loop Controller 从 Layer 2 读取当前 State。
   - 调用 Layer 3 LLM Caller（注入 System Prompt + Context Optimizer 处理后的上下文）。
   - 模型输出 Thought + Action（工具调用或 Final Answer）。
   - Layer 3 Action Dispatcher → Layer 1 执行工具 → 生成 Observation。
   - Observer 反馈 → 更新 Layer 2 State（可能触发 compaction）。
   - Layer 4 Guardrails/Evaluator 检查 → 决定 continue / end / escalate。
   - Layer 5 记录全过程。
3. **特殊情况**：
   - 错误：Layer 4 触发 recovery hook → retry 或 human。
   - 长任务：Layer 2 持久化 checkpoint → 支持暂停/恢复。
   - 多 Agent：Orchestrator 将子任务 spawn 为独立 Graph 子图，共享或同步 State。
4. **结束**：达到 termination condition（success / max iterations / user stop）→ Layer 5 汇总报告 → 返回最终输出。

**数据流**：State 是单向真理源（single source of truth）；所有组件通过 read/update State 协作，避免紧耦合。

**控制流**：Conditional Edges + Hooks 实现灵活路由。

### 4. 设计原则与权衡
- **可靠性优先**：处处加 guardrails、validation、limits（iterations、tokens、cost）。
- **可扩展性**：模块化（易插拔工具、模型 provider、中间件）。
- **可观测性**：所有决策/状态变更必须 traceable。
- **性能**：异步执行、并行工具调用、聪明 compaction。
- **演进性**：支持 self-harness（Agent 优化自身规则）。

这种分层设计让 **Agent Loop** 保持简单纯粹（ReAct 核心），而 **Runtime** 承担所有生产复杂性。实际实现时，我会先用 LangGraph 快速原型（它天然支持 StateGraph + checkpoints + persistence），再根据需要自定义 Layer 1/4/5 的生产增强。

这个架构在编码 Agent、自动化工作流等场景中都非常适用。如果你有特定领域（如 coding agent）或约束，我可以进一步细化某个层或画伪代码/图示。

## 三、验证、评估与反馈循环 / Verification, Evaluator, Feedback Loops

**验证、评估与反馈循环（Verification, Evaluator & Feedback Loops）** 是 Harness Engineering 中实现**可靠性与自愈性**的关键子系统。它直接对应“自我纠正、质量把关；失败时触发恢复或人类介入”的核心目标，是将不可靠的 LLM 循环转化为生产级 Agent 的“刹车 + 安全带 + 修复车间”。

### 1. 核心作用与设计目标
- **自我纠正（Self-Correction）**：Agent 在循环中发现问题后自动修复，而非直接输出错误结果。
- **质量把关（Quality Gate）**：在行动前后、输出前后设置检查点，确保符合规范、事实一致、无害。
- **失败恢复与介入（Failure Recovery & HITL）**：检测异常后，触发重试、回滚、子流程或暂停等待人类。
- **持续改进**：收集运行数据，用于迭代 Harness（prompts、rules、tools）。

**设计原则**：
- **多层防御**：预防（pre-emptive）+ 检测（runtime）+ 纠正（post-action）。
- **低延迟高覆盖**：轻量规则优先，重模型评估作为后备。
- **可配置与可审计**：所有检查结果进入 observability 系统。

### 2. 主要技术实现方式

#### **(1) Verification（验证）—— 确定性、规则驱动检查**
这是最快、最可靠的第一道防线，使用**非 LLM 或轻量 LLM** 实现。

- **技术组件**：
  - **Rule-based Validators / Guardrails**：正则、Schema 校验（Pydantic、JSON Schema）、代码 lint（ESLint、Ruff、Bandit）、安全扫描（prompt injection 检测、PII 脱敏）。
  - **Output Parsers & Format Enforcers**：强制模型输出结构化格式（JSON mode、Tool Calling、XML tags），失败则重试。
  - **Factuality / Consistency Checkers**：Embedding 相似度对比（与知识库或历史事实）、知识图谱验证。
  - **Domain-specific Checkers**：对于 Coding Agent——单元测试执行（pytest）、类型检查（mypy）、静态分析；对于 RAG——引用 faithfulness 检查。

- **实现示例**：
  - LangChain / LlamaIndex 的 Output Parsers + Guardrails AI / NeMo Guardrails。
  - Anthropic 的 Constitutional AI 或自定义 rules 文件（CLAUDE.md 风格）。
  - Hooks：在工具调用前/后、LLM 输出后立即执行（middleware pattern）。

#### **(2) Evaluator（评估器）—— 智能、模型驱动判断**
当规则不够用时，使用 LLM 或专用模型进行深度评估。

- **技术组件**：
  - **LLM-as-Judge**：专用 Evaluator Agent 或 Prompt，让模型打分（0-1 或 rubric-based：factuality、helpfulness、safety、completeness）。
  - **Multi-Perspective Evaluation**：多个小模型/不同 prompt 并行评估，取 consensus（多数投票或加权）。
  - **Reference-based vs Reference-free**：有 ground truth 时对比；无时用 self-consistency（多次采样投票）或 Chain-of-Verification（CoVe）。
  - **Reward Models / Critique Models**：微调或 prompt-based critic 模型，输出详细 critique + 修复建议。
  - **Task-specific Metrics**：Code——pass@k、执行成功率；General——BLEU/ROUGE、G-Eval、LLM Judge scores。

- **实现框架**：
  - LangSmith / LangFuse / Phoenix 的 Eval 模块。
  - DeepEval、RAGAS（针对 RAG）、OpenAI Evals。
  - Anthropic / OpenAI 的自定义 evaluator workflows。

#### **(3) Feedback Loops（反馈循环）—— 闭环驱动机制**
将 Verification + Evaluator 的结果反馈回 Agent，形成自适应系统。

- **技术组件**：
  - **Immediate Feedback**：在 ReAct 循环中，将 critique/observation 直接 append 到上下文，下一次 LLM 调用时参考。
  - **Reflection / Self-Refine**：专用 Reflection Step（“Review your previous actions and suggest improvements”）。
  - **Plan-Execute-Verify (PEV) 循环**：规划 → 执行 → 验证 → 修复 → 迭代。
  - **Hierarchical Feedback**：子 Agent 报告给 Supervisor Evaluator。
  - **Retry & Recovery Policies**：指数退避重试、alternative tool/route、rollback to last checkpoint。
  - **Human-in-the-Loop (HITL)**：阈值触发（confidence < 0.7 或 evaluator reject）→ 暂停、发送审批请求（通过 Slack/Email/Web UI）、注入人类反馈作为新 Observation。
  - **Long-term Learning**：运行日志 → 失败案例库 → 自动生成新 rules 或 fine-tune data（或更新 Harness prompts）。

- **实现模式**：
  - **StateGraph 中的 Conditional Edges**（LangGraph）：根据 evaluator score 路由到 “fix_node” 或 “human_node”。
  - **Middleware / Hooks**：pre/post hooks 链，支持异步执行。
  - **Event-Driven**：使用 Kafka / Redis Streams 发布验证事件，订阅者触发动作。
  - **Self-Improvement Loops**：定期 batch 分析日志，用另一个 Agent 生成 harness 改进建议。

### 3. 典型协作流程（在一个 Agent Loop 迭代中）
1. Agent 决策并输出 Action（工具调用或 Final Answer）。
2. **Pre-Execution Verification**：Guardrails 检查权限、安全 → 通过则执行。
3. Tool 执行 → 得到 raw Observation。
4. **Post-Execution Verification**：格式/安全/简单规则检查。
5. **Evaluator 评估**：LLM Judge 打分 + critique。
   - 通过（score > threshold）：继续循环或结束。
   - 轻微问题：Reflection → 反馈给下次循环（self-correct）。
   - 严重失败：触发 Recovery（retry / alternative plan）或 HITL。
6. 所有结果 + metadata 写入 Logging / Tracing。
7. State 更新，Loop Controller 决定下一步。

**示例伪流程（Python-like）**：
```python
def step(state):
    action = llm_call(state)  # Thought + Action
    if not guardrail.validate(action): 
        return recovery(state, "guardrail_fail")
    
    result = execute_tool(action)
    verification = rule_based_check(result)
    if not verification.ok:
        return fix(state, verification.critique)
    
    eval_score, critique = evaluator.evaluate(state, result)
    if eval_score < THRESHOLD:
        if should_human_in_loop(eval_score):
            return pause_for_human(state, critique)
        else:
            state["reflection"] = critique
            return step(state)  # re-loop with feedback
    
    update_state(state, result)
    return decide_next(state)
```

### 4. 实际落地中的最佳实践与挑战
- **分级评估**：规则（快）→ 轻量 critic → 完整 LLM Judge，平衡成本与准确性。
- **Benchmarking**：用 AgentBench、WebArena、GAIA 等评估整个 feedback 系统效果。
- **挑战**：
  - **Reward Hacking**：Evaluator 被模型“讨好”，需 adversarial testing。
  - **延迟/成本**：每个循环多 LLM 调用 → 优化为采样评估或缓存。
  - **False Positive**：过度保守导致卡住 → 可调阈值 + A/B 测试。
- **先进方向**：Process Supervision（过程监督而非结果）、Constitutional Classifiers、Agent 自我演化 harness。

这个子系统是 Harness 从“聪明”转向“可靠”的关键，往往占整个工程工作量的 30-50%。在编码 Agent 中，它直接体现为“写代码 → 跑测试 → 修复 → 验证通过”的自动化闭环。

如果你需要具体代码示例、某个场景（如 Coding Agent）的详细设计，或与 LangGraph 的集成方式，我可以进一步展开。
