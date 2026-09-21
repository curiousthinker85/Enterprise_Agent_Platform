from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ModelTestResponse
from app.services.llm_gateway import LLMGateway, LLMGatewayError, get_gateway

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/config")
def get_model_config(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "default_provider": settings.default_llm_provider,
        "default_model": settings.default_llm_model,
        "api_base_configured": bool(settings.default_llm_api_base),
        "api_key_configured": bool(settings.default_llm_api_key),
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }


@router.post("/test", response_model=ModelTestResponse)
async def test_model(gateway: LLMGateway = Depends(get_gateway)) -> ModelTestResponse:
    try:
        response = await gateway.chat(ChatRequest(messages=[ChatMessage(role="user", content="Reply only with: OK")], max_tokens=5))
    except LLMGatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ModelTestResponse(ok=True, model=response.model, message=response.content.strip())


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, gateway: LLMGateway = Depends(get_gateway)) -> ChatResponse:
    try:
        return await gateway.chat(request)
    except LLMGatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
