from trustai_api.routes.health import router as health_router
from trustai_api.routes.jobs import router as jobs_router
from trustai_api.routes.packs import router as packs_router
from trustai_api.routes.proofs import router as proofs_router
from trustai_api.routes.verify import router as verify_router

__all__ = [
    "health_router",
    "jobs_router",
    "packs_router",
    "proofs_router",
    "verify_router",
]
