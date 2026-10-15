from app.agent import Agent, AgentMaxStepsExceeded
from app.decision import Decision, ToolCall
from app.tools import build_registry


class FakeModel:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.calls = 0

    def decide(self, messages, tools):
        self.calls += 1
        return next(self.decisions)


def test_agent_calls_tool_and_finishes():
    model = FakeModel([
        Decision(
            type="tool_call",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    name="add",
                    arguments={"a": 12, "b": 30},
                )
            ],
        ),
        Decision(
            type="final",
            content="12 + 30 = 42",
        ),
    ])

    agent = Agent(
        model=model,
        tools=build_registry(),
        max_steps=5,
    )

    answer = agent.run("计算 12 + 30")

    assert answer == "12 + 30 = 42"
    assert model.calls == 2


def test_agent_stops_at_max_steps():
    model = FakeModel([
        Decision(
            type="tool_call",
            tool_calls=[
                ToolCall(
                    id=f"call_{i}",
                    name="add",
                    arguments={"a": 1, "b": 2},
                )
            ],
        )
        for i in range(10)
    ])

    agent = Agent(
        model=model,
        tools=build_registry(),
        max_steps=2,
    )

    try:
        agent.run("计算 1 + 2")
        assert False, "应该触发最大执行步数异常"
    except AgentMaxStepsExceeded:
        pass

    assert model.calls == 2


def test_unknown_tool_does_not_execute():
    model = FakeModel([
        Decision(
            type="tool_call",
            tool_calls=[
                ToolCall(
                    id="call_unknown",
                    name="delete_everything",
                    arguments={},
                )
            ],
        ),
        Decision(
            type="final",
            content="未知工具无法执行。",
        ),
    ])

    agent = Agent(
        model=model,
        tools=build_registry(),
        max_steps=5,
    )

    answer = agent.run("删除所有文件")

    assert answer == "未知工具无法执行。"