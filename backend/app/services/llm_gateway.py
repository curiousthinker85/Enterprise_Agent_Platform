import logging
import os
from typing import Any

# Do this before importing LiteLLM. It prevents a startup network call for pricing
# metadata, which is unnecessary for this gateway and unsafe for air-gapped installs.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

from app.core.config import Settings, get_settings
from app.schemas.chat import ChatRequest, ChatResponse, Usage

logger = logging.getLogger(__name__)


class LLMGatewayError(Exception):
    """A model provider could not process the request."""


class LLMGateway:
    """Provider-neutral Bring Your Own Model chat gateway."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _build_kwargs(self, request: ChatRequest) -> dict[str, Any]:
        model = request.model or self.settings.default_llm_model
        if not model:
            raise LLMGatewayError("No model configured. Set DEFAULT_LLM_MODEL or provide a model.")

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature if request.temperature is not None else self.settings.llm_temperature,
            "timeout": self.settings.request_timeout_seconds,
        }
        max_tokens = request.max_tokens if request.max_tokens is not None else self.settings.llm_max_tokens
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if self.settings.default_llm_api_key:
            kwargs["api_key"] = self.settings.default_llm_api_key
        if self.settings.default_llm_api_base:
            kwargs["api_base"] = self.settings.default_llm_api_base
        if self.settings.default_llm_api_version:
            kwargs["api_version"] = self.settings.default_llm_api_version
        return kwargs

    async def chat(self, request: ChatRequest) -> ChatResponse:
        kwargs = self._build_kwargs(request)
        model = kwargs["model"]
        logger.info("Calling LLM gateway | model=%s", model)
        try:
            # LiteLLM imports provider/tokenizer integrations. Keeping it lazy means
            # health checks, documentation and configuration remain available even
            # when a private deployment has no outbound internet access.
            import litellm
            from litellm import acompletion

            litellm.drop_params = True
            response = await acompletion(**kwargs)
            choice = response.choices[0]
            content = choice.message.content or ""
        except Exception as exc:
            logger.exception("LLM gateway call failed | model=%s", model)
            raise LLMGatewayError("The configured model could not be reached or process the request.") from exc

        usage_raw = getattr(response, "usage", None)
        usage = Usage(
            prompt_tokens=getattr(usage_raw, "prompt_tokens", None),
            completion_tokens=getattr(usage_raw, "completion_tokens", None),
            total_tokens=getattr(usage_raw, "total_tokens", None),
        ) if usage_raw else None
        return ChatResponse(
            id=getattr(response, "id", None),
            model=getattr(response, "model", model),
            content=content,
            usage=usage,
            provider=self.settings.default_llm_provider,
        )


_gateway: LLMGateway | None = None


def get_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
