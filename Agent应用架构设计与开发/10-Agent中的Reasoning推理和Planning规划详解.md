下面按 AI Agent 应用开发里常见的两个模块来讲：**Reasoning 负责“怎么想”**，**Planning 负责“怎么做”**。我查了 DeepSeek 官方文档：DeepSeek API 当前兼容 OpenAI SDK，`base_url` 是 `https://api.deepseek.com`；当前推荐模型包括 `deepseek-v4-pro`、`deepseek-v4-flash`，旧的 `deepseek-chat`、`deepseek-reasoner` 将在 `2026-07-24 15:59 UTC` 废弃。官方也支持 `thinking` 和 `reasoning_effort` 参数。参考：[DeepSeek Quick Start](https://api-docs.deepseek.com/)、[Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)。

**一、Reasoning 推理常用方法**

| 方法                        | 核心思想                     | 适合场景                   | 怎么用                       |
| --------------------------- | ---------------------------- | -------------------------- | ---------------------------- |
| Direct Reasoning            | 直接让模型回答               | 简单问答、分类、摘要       | 普通 prompt                  |
| Chain-of-Thought / Thinking | 让模型先推理再回答           | 数学、逻辑、代码、复杂判断 | DeepSeek `thinking enabled`  |
| Self-Consistency            | 同一问题多次推理，投票选答案 | 高风险判断、数学题         | 多次采样 + 聚合              |
| ReAct                       | Reason + Act，边想边调用工具 | 搜索、查库、执行函数       | LLM + tools 循环             |
| Self-Ask                    | 把复杂问题拆成子问题         | 多跳问答、业务规则推断     | 先生成子问题，再逐个回答     |
| Reflection / Critic         | 先回答，再自我检查修正       | 代码生成、方案评审         | answer -> critique -> revise |
| Tree of Thoughts            | 生成多个推理分支并搜索       | 谜题、策略、复杂决策       | BFS/DFS/评分器               |
| RAG-grounded Reasoning      | 基于检索材料推理             | 企业知识库、文档问答       | 检索 + 引用 + 回答           |

**二、Planning 规划常用方法**

| 方法                      | 核心思想                     | 适合场景                   | 怎么用                          |
| ------------------------- | ---------------------------- | -------------------------- | ------------------------------- |
| Plan-and-Execute          | 先生成计划，再逐步执行       | 大多数 Agent 任务          | planner + executor              |
| ReAct Planning            | 每一步观察环境后决定下一步   | 动态环境、工具调用         | thought/action/observation loop |
| HTN 分层任务网络          | 大任务拆成层级子任务         | 复杂业务流程               | 目标 -> 阶段 -> 原子动作        |
| DAG Planning              | 生成有依赖关系的任务图       | 数据流水线、多步骤工程任务 | JSON DAG + 拓扑执行             |
| State Machine             | 固定状态流转                 | 客服、审批、交易系统       | 状态 + 转移条件                 |
| Goal Decomposition        | 从目标反推必要步骤           | 研究、写作、项目管理       | goal -> milestones -> tasks     |
| Classical Planning / PDDL | 明确定义状态、动作、前置条件 | 自动化、机器人、规则系统   | 传统规划器 + LLM 解释           |
| Multi-agent Planning      | 多角色协作规划               | 复杂项目、评审、辩论       | planner/reviewer/executor 分工  |

下面给你一组可直接改造的 Python 代码。

先安装：

```
pip install -U openai
```

设置环境变量：

```
set DEEPSEEK_API_KEY=你的key
```

### 1. 基础 Reasoning：开启 Thinking 模式

```
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

def reasoning_answer(question: str):
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": "你是一个严谨的 AI Agent 推理模块。请给出简洁、可靠的最终答案。"},
            {"role": "user", "content": question},
        ],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    msg = response.choices[0].message

    # DeepSeek 可能返回 reasoning_content。生产环境通常不建议直接展示完整推理链，
    # 可以只展示最终答案或摘要化的理由。
    return {
        "answer": msg.content,
        "reasoning_debug": getattr(msg, "reasoning_content", None),
    }

result = reasoning_answer("9.11 和 9.8 哪个更大？请判断。")
print(result["answer"])
```

### 2. Self-Consistency：多次推理后投票

```
from collections import Counter

def ask_once(question: str) -> str:
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": "请只输出最终答案，不要展开推理过程。"},
            {"role": "user", "content": question},
        ],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    return response.choices[0].message.content.strip()

def self_consistency(question: str, n: int = 5):
    answers = [ask_once(question) for _ in range(n)]
    vote = Counter(answers).most_common(1)[0]
    return {
        "samples": answers,
        "final": vote[0],
        "votes": vote[1],
    }

result = self_consistency("一个商品原价100元，先涨价20%，再降价20%，最终价格是多少？")
print(result)
```

### 3. ReAct：模型决定是否调用工具

这个例子让 Agent 自己决定是否调用计算器。

```
import json
from openai import OpenAI

def calculator(expression: str) -> str:
    allowed = "0123456789+-*/(). "
    if not all(ch in allowed for ch in expression):
        return "表达式包含非法字符"
    return str(eval(expression))

tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "例如: (100 * 1.2) * 0.8"
                    }
                },
                "required": ["expression"],
            },
        },
    }
]

TOOL_MAP = {
    "calculator": calculator
}

def react_agent(question: str):
    messages = [
        {"role": "system", "content": "你是一个会使用工具的 Agent。需要计算时调用 calculator。"},
        {"role": "user", "content": question},
    ]

    while True:
        response = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            tools=tools,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = TOOL_MAP[name](**args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

answer = react_agent("一个商品原价100元，先涨价20%，再降价20%，最终价格是多少？")
print(answer)
```

### 4. Planning：先生成计划，再执行

适合 Agent 应用里的典型架构：`Planner -> Executor -> Summarizer`。

```
import json

def make_plan(goal: str):
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {
                "role": "system",
                "content": """
你是 AI Agent 的规划器。
请把用户目标拆成可执行步骤。
只输出 JSON，格式：
{
  "goal": "...",
  "steps": [
    {"id": 1, "task": "...", "tool": "llm|calculator|search|code", "depends_on": []}
  ]
}
"""
            },
            {"role": "user", "content": goal},
        ],
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}},
    )

    return json.loads(response.choices[0].message.content)

def execute_step(step):
    prompt = f"""
你是执行器。请完成这个任务：

任务：{step["task"]}
工具类型：{step["tool"]}

请输出执行结果。
"""
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"thinking": {"type": "disabled"}},
    )
    return response.choices[0].message.content

def plan_and_execute(goal: str):
    plan = make_plan(goal)
    results = []

    for step in plan["steps"]:
        output = execute_step(step)
        results.append({
            "step_id": step["id"],
            "task": step["task"],
            "result": output,
        })

    final_response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": "你是总结器。请基于执行结果给出最终答案。"},
            {"role": "user", "content": json.dumps(results, ensure_ascii=False)},
        ],
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    return {
        "plan": plan,
        "results": results,
        "final": final_response.choices[0].message.content,
    }

task = "帮我设计一个 AI Agent，用来自动分析销售日报并生成管理建议。"
result = plan_and_execute(task)

print("计划：")
print(json.dumps(result["plan"], ensure_ascii=False, indent=2))
print("\n最终答案：")
print(result["final"])
```

**实践建议**

简单任务用 `deepseek-v4-flash + thinking disabled`，便宜快。复杂推理、代码、规划、评审用 `deepseek-v4-pro + thinking enabled + reasoning_effort=high`。Agent 最常用组合是：

```
Planner：生成步骤
Executor：执行每一步
Tool Layer：搜索、数据库、计算器、代码执行
Memory：保存上下文
Verifier：检查结果
Summarizer：输出最终答案
```

最稳的工程形态通常是：

```
Reasoning 用来提高单步判断质量
Planning 用来控制多步任务流程
Tools 用来连接真实世界
Verifier 用来兜底纠错
```