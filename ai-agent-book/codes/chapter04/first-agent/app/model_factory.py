import os

from dotenv import load_dotenv

from .models import (
    AnthropicAdapter,
    OpenAICompatibleAdapter,
)

load_dotenv()


def create_model():
    provider = os.getenv(
        "MODEL_PROVIDER", "deepseek"
    ).lower()

    model = os.getenv("MODEL_NAME", "")

    if provider == "openai":
        return OpenAICompatibleAdapter(
            model=model or "gpt-4.1-mini",
            api_key=os.environ["OPENAI_API_KEY"],
        )

    if provider == "deepseek":
        return OpenAICompatibleAdapter(
            model=model or "deepseek-chat",
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.getenv(
                "DEEPSEEK_BASE_URL",
                "https://api.deepseek.com",
            ),
        )

    if provider == "ollama":
        return OpenAICompatibleAdapter(
            model=model,
            api_key="ollama",
            base_url=os.getenv(
                "OLLAMA_BASE_URL",
                "http://localhost:11434/v1",
            ),
        )

    if provider == "anthropic":
        return AnthropicAdapter(
            model=model or "claude-sonnet-4-5"
        )

    raise ValueError(f"不支持的模型供应商: {provider}")