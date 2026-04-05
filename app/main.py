from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="webhook-relay",
        description="Receives, verifies, deduplicates, and reliably delivers webhook events.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.v1.health import router as health_router
    app.include_router(health_router)

    return app


app = create_app()
