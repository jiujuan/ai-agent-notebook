亲手实现第一个 Agent——从模型调用到 Agent Loop。

这一篇进一步回答一个工程问题：

**如何使用 Python 3，从零开始编写一个真正调用 LLM API、能够执行工具、接收工具结果、继续请求模型，并且知道何时停止的 Agent？**

本篇为实战教程。

## 一、先确定本篇的学习目标

完成后，读者不只是理解 Agent 的概念，而是能够运行一个具有以下行为的程序：

1. 接收用户提出的任务。
2. 请求真实 LLM 判断下一步应该做什么。
3. 根据模型的结构化决策，调用经过注册的工具。
4. 将工具执行结果反馈给模型。
5. 让模型根据真实结果决定继续行动还是返回答案。
6. 在任务完成、执行失败或达到最大步数时，合理结束运行。

这里有一个重要的教学原则：先实现一个最小但真实的 Agent，再逐步增加工程能力，而不是一开始就引入完整的 Agent 框架。

## 二、设计整个实战项目

我们不直接从几十行代码开始，而是先确定系统结构，避免后面随着功能增加，不断推翻已有实现。

### 2.1 本篇采用的技术栈

| 技术          | 用途                               |
| ------------- | ---------------------------------- |
| Python 3.11+  | Agent 核心实现语言                 |
| OpenAI SDK    | 调用 OpenAI 及兼容其接口的模型服务 |
| Anthropic SDK | 调用 Claude 模型                   |
| Pydantic      | 定义和校验结构化决策结果           |
| pytest        | 自动化测试                         |
| python-dotenv | 加载环境变量与本地开发配置         |

为了让示例更容易理解，我们暂时不引入 LangGraph、LangChain 或其他完整 Agent 框架。我们自己实现模型适配器、工具执行器和 Agent Loop，理解每个组件到底在做什么。

需要注意：DeepSeek 和 Ollama 的具体接入方式取决于服务版本、接口协议和所用模型。OpenAI 兼容接口可以复用同一适配器，但 Anthropic 使用自己的消息与工具调用协议，因此需要单独的适配器。

### 2.2 项目目录

建议创建一个名为 `first-agent` 的项目。

![](../../images/AI-Agent-ARCH-first-agent-project.png)

这个结构刻意保持简单，但已经体现了几个重要的架构边界：

- `models.py` 不负责执行工具。
- `tools.py` 不负责决定下一步行动。
- `agent.py` 不需要了解不同模型供应商的底层响应格式。
- `decision.py` 定义各组件之间交换的数据结构。

这意味着后面即使更换模型、增加工具或者改进执行循环，也不必把所有代码一起修改。

## 三、第一步：搭建 Python 开发环境

### 3.1 创建项目和虚拟环境

在终端执行：

```bash
mkdir first-agent
cd first-agent

python -m venv .venv
```

激活虚拟环境。

- Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

- macOS 或 Linux：

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install openai anthropic pydantic python-dotenv pytest
```

