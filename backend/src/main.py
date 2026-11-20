"""FastAPI application entrypoint: Dishka container, CORS, exception handlers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import api_router
from src.clients.keitaro import KeitaroAPIError
from src.core.ioc import AppProvider
from src.services.auth import AuthError
from src.services.stream_editor import StreamValidationError

container: AsyncContainer = make_async_container(AppProvider())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: close DI container (and its httpx pool) on shutdown."""
    yield
    await container.close()


app = FastAPI(title="Keitaro Manager API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_dishka(container, app)

app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe for docker-compose healthcheck."""
    return {"status": "ok"}


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """401 для неверных кредов и недействительных токенов."""
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(StreamValidationError)
async def stream_validation_handler(request: Request, exc: StreamValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.message})


@app.exception_handler(KeitaroAPIError)
async def keitaro_error_handler(request: Request, exc: KeitaroAPIError) -> JSONResponse:
    """Map Keitaro API failures to upstream HTTP responses."""
    status = exc.status_code if 400 <= exc.status_code < 600 else 502
    return JSONResponse(status_code=status, content={"detail": f"Keitaro API: {exc.message}"})
