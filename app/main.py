from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(
        title="webhook-relay",
        description="Receives, verifies, deduplicates, and reliably delivers webhook events.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.v1.health import router as health_router
    from app.api.v1.webhooks import router as webhooks_router
    from app.api.v1.events import router as events_router
    app.include_router(health_router)
    app.include_router(webhooks_router)
    app.include_router(events_router)

    return app


app = create_app()
