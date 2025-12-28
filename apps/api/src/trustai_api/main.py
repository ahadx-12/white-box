from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trustai_api.deps import init_app_state
from trustai_api.routes import (
    health_router,
    jobs_router,
    packs_router,
    proofs_router,
    verify_router,
)


def create_app() -> FastAPI:
    app = FastAPI(title="TrustAI API", version="0.3.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(verify_router)
    app.include_router(jobs_router)
    app.include_router(proofs_router)
    app.include_router(packs_router)

    @app.on_event("startup")
    def startup() -> None:
        init_app_state(app)

    return app
