import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.rate_limiting import limiter
from app.api.routes.admin import router as admin_router
from app.api.routes.cases import router as cases_router
from app.api.routes.health import router as health_router
from app.api.routes.hints import router as hints_router
from app.api.routes.players import router as players_router
from app.api.routes.scores import router as scores_router

app = FastAPI(title="Tiny Detective API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ALLOWED_ORIGINS is unset (-> "*") for local dev, where the Flutter web app
# runs on a different origin/port and any origin is fine. Set to the real
# Firebase Hosting origin in the Cloud Run deploy (Phase 8) so a browser
# can't call this API cross-origin from anywhere else.
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_allowed_origins] if _allowed_origins != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(cases_router)
app.include_router(hints_router)
app.include_router(players_router)
app.include_router(scores_router)
app.include_router(admin_router)
