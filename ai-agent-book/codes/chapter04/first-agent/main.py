import logging

from app.agent import Agent
from app.model_factory import create_model
from app.tools import build_registry


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def main():
    model = create_model()
    tools = build_registry()

    agent = Agent(
        model=model,
        tools=tools,
        max_steps=8,
    )

    answer = agent.run(
        "请使用计算工具计算 12345 + 67890，"
        "并解释计算结果。"
    )

    print("\n最终答案：")
    print(answer)


if __name__ == "__main__":
    main()