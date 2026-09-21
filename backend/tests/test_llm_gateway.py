from app.core.config import Settings
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.llm_gateway import LLMGateway


def settings() -> Settings:
    return Settings(
        default_llm_provider="openai",
        default_llm_model="test-default-model",
        llm_temperature=0.1,
        llm_max_tokens=100,
    )


def test_gateway_uses_configured_defaults() -> None:
    kwargs = LLMGateway(settings())._build_kwargs(
        ChatRequest(messages=[ChatMessage(role="user", content="Hello")])
    )
    assert kwargs["model"] == "test-default-model"
    assert kwargs["temperature"] == 0.1
    assert kwargs["max_tokens"] == 100


def test_gateway_allows_safe_request_overrides() -> None:
    kwargs = LLMGateway(settings())._build_kwargs(
        ChatRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="override-model",
            temperature=0.5,
            max_tokens=50,
        )
    )
    assert kwargs["model"] == "override-model"
    assert kwargs["temperature"] == 0.5
    assert kwargs["max_tokens"] == 50
