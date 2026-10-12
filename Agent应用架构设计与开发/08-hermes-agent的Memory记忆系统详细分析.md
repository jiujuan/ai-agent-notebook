

Hermes Agent 的记忆系统是目前开源 Agent 领域设计得比较成熟的一套方案之一。它并不是简单的「向量数据库+RAG」，而是采用了**分层记忆（Layered Memory）架构**，将不同类型的信息放在不同层级管理。([Hermes Agent](https://hermes-agent.ai/blog/hermes-agent-memory-system?utm_source=chatgpt.com))

# 一、Hermes Memory总体架构

Hermes的核心思想：

> 不同的信息应该存储在不同的记忆层中。

官方和社区资料总结后，可以抽象成：

```text
                用户输入
                     │
                     ▼

        ┌─────────────────────┐
        │ Working Memory      │
        │ 当前上下文窗口       │
        └─────────────────────┘
                     │
                     ▼

        ┌─────────────────────┐
        │ Persistent Memory   │
        │ MEMORY.md           │
        │ USER.md             │
        └─────────────────────┘
                     │
                     ▼

        ┌─────────────────────┐
        │ Episodic Memory     │
        │ 历史任务与对话      │
        │ 向量检索            │
        └─────────────────────┘
                     │
                     ▼

        ┌─────────────────────┐
        │ Skills System       │
        │ 经验与流程沉淀      │
        └─────────────────────┘
```

这实际上已经接近认知科学中的：

- Working Memory（工作记忆）
- Semantic Memory（语义记忆）
- Episodic Memory（情景记忆）
- Procedural Memory（程序性记忆）

设计思想。([Hermes Agent](https://hermes-agent.ai/blog/hermes-agent-memory-system?utm_source=chatgpt.com))

------

# 二、第一层：Working Memory（工作记忆）

这是最简单的一层。

本质：

```text
LLM Context Window
```

即：

```text
System Prompt
+
Memory Snapshot
+
当前对话
+
工具结果
```

特点：

| 属性     | 说明          |
| -------- | ------------- |
| 生命周期 | 单会话        |
| 速度     | 最快          |
| 容量     | 受Context限制 |
| 作用     | 当前推理      |

例如：

```text
用户：
帮我分析Spring项目

Agent：
读取代码...
```

整个分析过程都存在当前Context里。

但：

```text
关闭会话
```

后：

```text
全部消失
```

因此需要长期记忆层。([Hermes Agent](https://hermes-agent.ai/features/persistent-memory?utm_source=chatgpt.com))

------

# 三、第二层：Persistent Memory（持久记忆）

这是Hermes最有特色的设计之一。

官方采用两个文件：

```text
~/.hermes/memories/

├── MEMORY.md
└── USER.md
```

([Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/?utm_source=chatgpt.com))

------

## MEMORY.md

存放：

```text
环境事实
项目事实
约定
经验
```

例如：

```markdown
- 公司项目使用Spring Boot 3
- 所有服务部署在K8S
- Redis统一使用JSON序列化
```

------

## USER.md

存放：

```text
用户偏好
沟通方式
工作背景
```

例如：

```markdown
- 用户喜欢中文回答
- 用户是技术管理者
- 回答优先提供架构视角
```

------

## 为什么不用Vector DB？

很多Agent：

```text
用户信息
↓
Embedding
↓
Vector DB
```

Hermes没有这么做。

原因：

### Prompt Cache

Hermes把Memory直接注入System Prompt。

```text
System Prompt

Memory Snapshot

Current Conversation
```

这样：

```text
Memory永远在模型注意力范围内
```

无需检索。

因此：

- 更稳定
- 延迟更低
- 成本更低

([Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/?utm_source=chatgpt.com))

------

## Memory容量限制

官方限制：

| 文件      | 大小     |
| --------- | -------- |
| MEMORY.md | 2200字符 |
| USER.md   | 1375字符 |

约：

```text
1300 Token左右
```

([Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/?utm_source=chatgpt.com))

------

### 为什么限制这么小？

因为Hermes认为：

> 长期记忆应该保存最重要的信息，而不是保存全部信息。

否则：

```text
Memory越来越大
↓
Prompt越来越长
↓
推理成本越来越高
```

因此采用：

```text
Summarize
Compress
Replace
```

策略。([Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/?utm_source=chatgpt.com))

------

# 四、第三层：Episodic Memory（情景记忆）

这一层解决：

```text
Memory太小
```

的问题。

官方称：

```text
Session Search
```

或

```text
Episodic Memory
```

([Hermes Agent](https://hermes-agent.ai/blog/hermes-agent-memory-system?utm_source=chatgpt.com))

------

## 存储什么？

例如：

```text
2026-06-01
修复支付Bug

2026-06-05
设计用户增长系统

2026-06-10
优化Spring链路追踪
```

每次任务：

```text
做了什么
结果如何
成功还是失败
```

都会记录。

------

## 技术实现

社区分析显示主要采用：

```text
SQLite
+
FTS5
+
Embedding Search
```

或者：

```text
ChromaDB
```

实现。([Remote OpenClaw](https://www.remoteopenclaw.com/blog/hermes-agent-memory-system-explained?utm_source=chatgpt.com))

------

## 查询过程

用户：

```text
上周那个支付问题怎么解决的？
```

Agent：

```text
Query
 ↓
Session Search
 ↓
找到历史任务
 ↓
注入Context
 ↓
回答
```

形成：

```text
Recall → Reason
```

流程。([Hermes Agent](https://hermes-agent.ai/blog/hermes-agent-memory-system?utm_source=chatgpt.com))

------

# 五、第四层：Skills（技能记忆）

这是很多Agent没有的部分。

Hermes把：

```text
成功完成的流程
```

抽象成：

```text
Skill
```

([Hermes Agent](https://hermes-agent.ai/blog/hermes-agent-memory-system?utm_source=chatgpt.com))

------

例如：

Agent学会：

```text
部署Spring服务
```

之后形成：

```markdown
Skill:
Deploy Spring Service

1. Build Jar
2. Build Docker Image
3. Push Registry
4. Deploy K8S
5. Verify Health
```

下次：

```text
再部署
```

时直接调用Skill。

------

这实际上属于认知科学里的：

```text
Procedural Memory
```

程序性记忆。

类似人类：

```text
学会开车
学会骑自行车
```

之后不需要重新思考。([Hermes Agent](https://hermes-agent.ai/blog/hermes-agent-memory-system?utm_source=chatgpt.com))

------

# 六、Hermes为什么比很多Agent记忆效果好

因为它没有只依赖RAG。

很多Agent：

```text
所有东西
↓
Embedding
↓
Vector Search
```

问题：

```text
召回不稳定
容易漏
语义漂移
```

------

Hermes采用：

```text
热记忆
+
长期事实
+
历史事件
+
技能经验
```

四层结构。

```text
Working Memory
      ↓
Semantic Memory
      ↓
Episodic Memory
      ↓
Procedural Memory
```

实际上接近人脑模型。

([Hermes Agent](https://hermes-agent.ai/blog/hermes-agent-memory-system?utm_source=chatgpt.com))

------

# 七、从Agent架构角度看Hermes

如果你正在构建自己的AI商业系统或AI Agent平台，可以借鉴Hermes，把记忆设计成四层：

```text
Layer 1
短期工作记忆
(Redis)

Layer 2
用户画像记忆
(Postgres)

Layer 3
历史事件记忆
(Vector DB + FTS)

Layer 4
技能库
(Knowledge Base)
```

对于你正在研究的：

- AI营销系统
- 客户洞察系统
- AI职业规划顾问
- 多Agent商业系统

推荐进一步升级为：

```text
Working Memory
        +
Semantic Memory
        +
Episodic Memory
        +
Procedural Memory
        +
Knowledge Graph Memory
```

这会比Hermes官方实现更适合企业级长期运营场景，因为能够同时管理：

- 用户画像
- 项目历史
- 业务规则
- 工作流经验
- 实体关系网络

形成真正的 Agent Memory OS。

## 参考

- https://www.majiabin.com/hermes/getting-started/quickstart
- https://hermes-agent.nousresearch.com/docs/zh-Hans/user-guide/features/memory
- https://hermes-agent.ai/features/persistent-memory
- https://hermes-agent.ai/blog/hermes-agent-memory-system