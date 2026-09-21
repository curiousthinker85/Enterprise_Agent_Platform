from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import audit, auth, documents, health, members, models, workspaces
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import configure_logging
from app.services.llm_gateway import LLMGatewayError
from app.services.vector_store import get_vector_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    # Import the models before metadata creation so every table is registered.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    get_vector_store()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(models.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(workspaces.router, prefix="/api/v1")
    app.include_router(members.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")

    @app.exception_handler(LLMGatewayError)
    async def llm_gateway_error_handler(request: Request, exc: LLMGatewayError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc), "path": str(request.url.path)})

    return app


app = create_app()
