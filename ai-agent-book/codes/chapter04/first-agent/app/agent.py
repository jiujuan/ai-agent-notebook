import json
import logging
from typing import Any

from .decision import Decision
from .models import ModelClient
from .tools import ToolRegistry

logger = logging.getLogger("first_agent")


class AgentError(Exception):
    pass


class AgentMaxStepsExceeded(AgentError):
    pass


class Agent:
    def __init__(
        self,
        model: ModelClient,
        tools: ToolRegistry,
        max_steps: int = 8,
    ):
        if max_steps < 1:
            raise ValueError("max_steps 必须大于 0")

        self.model = model
        self.tools = tools
        self.max_steps = max_steps

    def run(self, user_input: str) -> str:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "你是一个能够使用工具的助手。"
                    "需要精确计算时，请使用提供的工具。"
                    "必须根据工具的真实返回值回答，"
                    "不要声称执行了实际上没有执行的操作。"
                ),
            },
            {
                "role": "user",
                "content": user_input,
            },
        ]

        for step in range(1, self.max_steps + 1):
            logger.info("Step %s: 请求模型决策", step)

            decision = self.model.decide(
                messages=messages,
                tools=self.tools.definitions(),
            )

            logger.info(
                "Step %s: 决策类型=%s",
                step,
                decision.type,
            )

            if decision.type == "final":
                if decision.tool_calls:
                    raise AgentError(
                        "最终决策不能同时包含工具调用"
                    )

                logger.info("任务完成")
                return decision.content

            if decision.type != "tool_call":
                raise AgentError(
                    f"未知决策类型: {decision.type}"
                )

            if not decision.tool_calls:
                raise AgentError(
                    "工具调用决策没有包含工具请求"
                )

            # 保存助手发出的工具调用请求
            messages.append({
                "role": "assistant",
                "content": decision.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "name": call.name,
                        "arguments": call.arguments,
                    }
                    for call in decision.tool_calls
                ],
            })

            for call in decision.tool_calls:
                logger.info(
                    "执行工具: %s, 参数=%s",
                    call.name,
                    call.arguments,
                )

                try:
                    tool = self.tools.get(call.name)
                    result = tool.execute(call.arguments)

                    tool_message = {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            result,
                            ensure_ascii=False,
                        ),
                    }

                    logger.info(
                        "工具 %s 执行成功",
                        call.name,
                    )

                except Exception as exc:
                    # 将工具错误作为观察结果反馈给模型。
                    # 注意：记录完整异常到服务端日志；
                    # 不向模型暴露密钥、堆栈或内部敏感信息。
                    logger.exception(
                        "工具 %s 执行失败",
                        call.name,
                    )

                    tool_message = {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {
                                "error": type(exc).__name__,
                                "message": "工具执行失败，请根据错误调整操作。",
                            },
                            ensure_ascii=False,
                        ),
                        "is_error": True,
                    }

                messages.append(tool_message)

        raise AgentMaxStepsExceeded(
            f"Agent 达到最大执行步数: {self.max_steps}"
        )