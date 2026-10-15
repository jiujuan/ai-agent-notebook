import json
import os

from openai import OpenAI
from anthropic import Anthropic

from abc import ABC, abstractmethod
from typing import Any

from .decision import Decision, ToolCall


class ModelClient(ABC):
    @abstractmethod
    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Decision:
        """根据消息和工具定义，返回统一决策。"""
        raise NotImplementedError

class OpenAICompatibleAdapter(ModelClient):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.model = model
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY") or "ollama",
            base_url=base_url or None,
            timeout=60.0,
            max_retries=0,
        )

    def decide(self, messages, tools) -> Decision:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=to_openai_messages(messages),
            tools=tools or None,
            temperature=0,
        )

        message = response.choices[0].message

        if message.tool_calls:
            calls = []

            for call in message.tool_calls:
                calls.append(
                    ToolCall(
                        id=call.id,
                        name=call.function.name,
                        arguments=json.loads(
                            call.function.arguments or "{}"
                        ),
                    )
                )

            return Decision(
                type="tool_call",
                tool_calls=calls,
            )

        return Decision(
            type="final",
            content=message.content or "",
        )

class AnthropicAdapter(ModelClient):
    def __init__(self, model: str):
        self.model = model
        self.client = Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            timeout=60.0,
            max_retries=0,
        )

    def decide(self, messages, tools) -> Decision:
        system_parts = []
        conversation = []

        for message in messages:
            role = message["role"]

            if role == "system":
                system_parts.append(message["content"])

            elif role == "user":
                conversation.append({
                    "role": "user",
                    "content": message["content"],
                })

            elif role == "assistant":
                blocks = []

                if message.get("content"):
                    blocks.append({
                        "type": "text",
                        "text": message["content"],
                    })

                for call in message.get("tool_calls", []):
                    blocks.append({
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call["arguments"],
                    })

                conversation.append({
                    "role": "assistant",
                    "content": blocks or [{
                        "type": "text",
                        "text": "",
                    }],
                })

            elif role == "tool":
                conversation.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": message["tool_call_id"],
                        "content": message["content"],
                        "is_error": message.get("is_error", False),
                    }],
                })

        anthropic_tools = [
            {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"],
            }
            for tool in tools
        ]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system="\n\n".join(system_parts),
            messages=conversation,
            tools=anthropic_tools or [],
        )

        calls = []
        texts = []

        for block in response.content:
            if block.type == "tool_use":
                calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )
            elif block.type == "text":
                texts.append(block.text)

        if calls:
            return Decision(
                type="tool_call",
                tool_calls=calls,
            )

        if response.stop_reason == "max_tokens":
            raise RuntimeError("模型输出达到 token 上限，答案可能不完整")

        return Decision(
            type="final",
            content="\n".join(texts),
        )

def to_openai_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []

    for message in messages:
        role = message["role"]

        if role in ("system", "user"):
            result.append({
                "role": role,
                "content": message["content"],
            })

        elif role == "assistant":
            item = {
                "role": "assistant",
                "content": message.get("content") or None,
            }

            calls = message.get("tool_calls", [])

            if calls:
                item["tool_calls"] = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(
                                call["arguments"],
                                ensure_ascii=False,
                            ),
                        },
                    }
                    for call in calls
                ]

            result.append(item)

        elif role == "tool":
            result.append({
                "role": "tool",
                "tool_call_id": message["tool_call_id"],
                "content": message["content"],
            })

        else:
            raise ValueError(f"不支持的消息角色: {role}")

    return result