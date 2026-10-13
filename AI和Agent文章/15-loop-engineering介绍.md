## Loop engineering 介绍

Loop engineering 不是一个特别统一的标准术语。更准确地说，它是一组 *把 AI agent 的循环过程工程化* 的实践。

一句话：
*agent loop 是 agent 运行时的基本循环；loop engineering 是设计、约束、观测、优化这个循环的工程方法。*

最典型的 agent loop 长这样：

```
用户目标
  ↓
模型思考 / 规划
  ↓
调用工具 / 执行动作
  ↓
拿到观察结果
  ↓
更新状态
  ↓
继续下一轮，直到完成或停止
```

比如 ReAct 论文里讲的就是这种“reasoning + acting”交替：模型一边推理，一边采取动作，再根据外部反馈继续调整。参考：[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)。

而 loop engineering 关心的是：这个循环怎么做才不会失控、烧钱、胡编、卡死、难调试。

它通常包括这些内容：

1. *循环边界设计*
   定义什么时候开始、什么时候结束、最多跑几轮、失败后怎么退出。没有边界的 agent 很容易陷入“再试一次”的死循环。
2. *状态设计*
   每一轮保留什么信息？任务目标、已尝试步骤、工具结果、错误、用户偏好、当前计划，都要有结构化状态，而不是全塞进聊天上下文。
3. *工具调用设计*
   工具 schema 怎么写、参数怎么校验、失败怎么重试、哪些工具需要权限、哪些工具只能读不能写。
4. *规划与执行分离*
   简单 agent 是“边想边做”。更稳的系统会拆成 planner、executor、verifier、recoverer。这样出错时知道是计划错了、工具错了，还是结果验证没过。
5. *验证循环*
   agent 做完一件事后，不是直接相信它，而是跑测试、断言、规则检查、LLM judge、人审或业务校验。
6. *恢复循环*
   遇到错误时，是重试、换工具、缩小任务、回滚，还是请求用户介入？这些都要明确。
7. *成本与预算控制*
   控制 token、工具调用次数、运行时间、并发数、最大反思次数。否则 agent 看似聪明，账单也很聪明。
8. *可观测性*
   记录每轮输入、模型输出、工具调用、耗时、错误、成本、最终结果。否则 debug agent 就像看一场没有录像的事故。
9. *人类介入点*
   哪些动作必须让人确认？比如付款、删数据、发邮件、改生产配置。这属于 human-in-the-loop engineering。
10. *离线改进循环*
       把失败案例收集起来，改 prompt、改工具、改评测、改流程，再回归测试。

它解决的问题主要是这些：

- agent 跑偏：目标越做越歪。
- agent 卡住：一直重复类似动作。
- agent 胡编：工具失败后自己补故事。
- agent 太贵：多轮工具调用把成本放大。
- agent 不可调试：只看到最终答案，不知道中间发生了什么。
- agent 不安全：随便调用高权限工具。
- agent 不稳定：同一个任务今天成功，明天失败。

和 agent loop 的区别可以这样看：

| 项目     | agent loop               | loop engineering                         |
| -------- | ------------------------ | ---------------------------------------- |
| 性质     | 运行机制                 | 工程方法                                 |
| 关注点   | 下一步做什么             | 怎么让每一步可靠、可控、可观测           |
| 粒度     | 单个执行循环             | 循环结构、状态、工具、评测、恢复、预算   |
| 典型问题 | think-act-observe-repeat | stop、retry、verify、trace、cost、safety |
| 类比     | 发动机运转               | 设计发动机、仪表盘、刹车、保养流程       |

它们的联系是：loop engineering 通常围绕 agent loop 展开。先有一个“模型-工具-观察”的基本循环，然后工程师把它变成一个能上线的系统。

但更进一步，loop engineering 也可能会削弱或替代原始 agent loop。比如 2026 年一篇论文把传统 agent loop 批评为“隐式依赖、恢复无界、历史可变”，提出用更显式的结构化图来管理执行流程。参考：[From Agent Loops to Structured Graphs](https://arxiv.org/abs/2604.11378)。

所以可以粗暴但好用地理解：

```
agent loop = agent 自己怎么一轮轮干活
loop engineering = 人怎么设计这个“一轮轮干活”的系统
```

再浓缩一点：

*agent loop 是循环。loop engineering 是给循环加方向盘、刹车、仪表盘、护栏和验收标准。*

相关参考还可以看：

- [ReAct](https://arxiv.org/abs/2210.03629)：早期经典的“推理-行动-观察”模式。

- [From Agent Loops to Structured Graphs](https://arxiv.org/abs/2604.11378)：讨论 agent loop 的结构性弱点。

- [EurekAgent](https://arxiv.org/abs/2606.13662)：把权限、环境、预算、人类监督作为 agent 工程的一部分。

- [Efficient Agents](https://arxiv.org/abs/2508.02694)：讨论 agent 系统的复杂度、成本和效果权衡。

  

## 几个 loop 循环

在 AI Agent 开发中，**Loop Engineering（循环工程）** 旨在将“发现任务、调用执行、验证结果、调整修正”的过程设计为自动化运行的稳定循环，从而让 Agent 具备持续推进任务的能力。 [[1](https://cloud.tencent.com/developer/article/2686567), [2](https://cloud.tencent.com/developer/article/2686804)]

根据吴恩达（Andrew Ng）等行业专家的系统性划分，AI Agent 开发通常涉及 **3 个不同时间尺度的循环**，层层嵌套以控制产品开发： [[1](https://aicoding.csdn.net/6a445c47662f9a54cb8718d7.html), [2](https://agent.csdn.net/6a45b41a10ee7a33f2858dfd.html)]

### 1、**Agentic Coding Loop (代码智能体循环)**

这是最内层的自动化工程循环（时间尺度：分钟级）。 [[1](https://aicoding.csdn.net/6a445c47662f9a54cb8718d7.html)]

- **工作原理**：给定产品规格说明书（Spec）和评测标准（Evals），Agent 会自主执行写代码、运行测试、观察报错、修复 Bug 的流程，直到测试全部通过。

- **人类角色**：设定边界与验收标准。

- **常见模式**：如 Retry Loop（简单重试）、Self-Correction（自我纠错）等。 [[1](https://www.runoob.com/ai-agent/loop-engineering.html), [2](https://xmsumi.com/detail/3689), [3](https://zhuanlan.zhihu.com/p/2050552845217294005), [4](https://aicoding.csdn.net/6a445c47662f9a54cb8718d7.html)]


### 2、Developer Feedback Loop (开发者反馈循环)

中间层循环，由开发者主导（时间尺度：小时级）。 [[1](https://aicoding.csdn.net/6a445c47662f9a54cb8718d7.html)]

- **工作原理**：开发者定期 Review Agent 产出的版本和当前产品状态，决定项目发展方向是否正确，并将模糊愿景精准翻译为可执行的 Spec，为内层循环指明方向。
- **人类角色**：上下文注入与航线修正。 [[1](https://aicoding.csdn.net/6a445c47662f9a54cb8718d7.html)]

### 3、External Feedback Loop (外部反馈循环)

最外层的市场验证循环，决定产品的最终成败（时间尺度：天/周级）。 [[1](https://aicoding.csdn.net/6a445c47662f9a54cb8718d7.html)]

- **工作原理**：通过 Alpha 测试、A/B 测试、真实用户访谈和数据埋点等收集真实世界反馈，修正产品愿景。
- **人类角色**：最终方向的把关者。 [[1](https://aicoding.csdn.net/6a445c47662f9a54cb8718d7.html)]



### 常见的具体工程执行模式（实现层面）

在设计 Agent 的代码逻辑时，还会用到以下具体的循环控制结构： [[1](https://zhuanlan.zhihu.com/p/2049892118655668801), [2](https://zhuanlan.zhihu.com/p/2050552845217294005)]

- **Retry Loop (重试循环)**：最基础的循环，逻辑为：执行 -> 检查（成功/失败） -> 失败则重试 -> 通过则停止。 [[1](https://zhuanlan.zhihu.com/p/2050552845217294005)]
- **Refinement Loop (精炼循环)**：Agent 初步生成结果后，引入自动化审查（如 LLM-as-Judge 工具），基于反馈循环进行多轮修改打磨。 [[1](https://aicoding.csdn.net/6a445c47662f9a54cb8718d7.html), [2](https://cloud.tencent.com/developer/article/2686567)]
- **Tool-use Loop (工具调用循环)**：Agent 感知问题 -> 触发行动（调用工具） -> 观察结果 -> 再次感知（Perceive-Reason-Act-Observe），直到任务真正完成。



- https://www.runoob.com/ai-agent/loop-engineering.html  loop engineering ，loop 循环
- https://github.com/cobusgreyling/loop-engineering/blob/main/LOOP.md
- https://github.com/cobusgreyling/loop-engineering