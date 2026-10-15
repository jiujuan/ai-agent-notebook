# First Agent

使用 Python 3 从零实现第一个 Agent。

## 功能

- 接入真实 LLM API
- 支持 OpenAI 兼容接口
- 支持 Anthropic Messages API
- 统一模型决策结构
- 工具注册、参数校验与执行
- Agent Loop 与最大执行步数
- 工具结果反馈
- 日志与单元测试

## 环境要求

- Python 3.10+
- 可用的 LLM API，或已启动的 Ollama 服务

## 安装

创建并激活 Python 虚拟环境，然后执行：

```bash
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，
填写模型供应商、模型名称和对应 API Key。

## 运行

```bash
python main.py
```

## 测试

```bash
pytest -v
```

## 项目结构

- app/decision.py：统一决策协议
- app/models.py：模型接口与适配器
- app/model_factory.py：模型工厂
- app/tools.py：工具注册与执行
- app/agent.py：Agent Loop
- tests/test_agent.py：单元测试
- main.py：程序入口

## 学习目标

理解模型决策、工具执行、结果反馈和停止条件，
为后续实现 Agent Runtime、Memory、Workflow
与多 Agent 协作系统打下基础。