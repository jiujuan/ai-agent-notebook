from typing import Any, Literal
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Decision(BaseModel):
    type: Literal["final", "tool_call"]
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)