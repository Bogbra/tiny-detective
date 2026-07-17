import os
import sys

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
from app.infrastructure.firestore.firestore_client import is_firestore_configured


def _require_persistent_storage_if_configured() -> None:
    """Fails fast at import time if REQUIRE_PERSISTENT_STORAGE=true but
    Firestore isn't actually configured — e.g. a Cloud Run deploy that
    forgot to set GOOGLE_CLOUD_PROJECT. Without this, the app would start
    fine and silently fall back to in-memory storage: every player, hint,
    and attempt would vanish on the next cold start, with nothing anywhere
    reporting an error. /health doesn't touch storage, so deploy.yml's smoke
    test alone can't catch this — crashing here is what makes it catch it:
    uvicorn fails to import the app, the container never becomes healthy,
    and the smoke test's curl gets a connection failure instead of a false
    200.

    REQUIRE_PERSISTENT_STORAGE is set only in the Cloud Run deploy (see
    deploy.yml) — unset locally and in tests, so this is a no-op everywhere
    except the one place it needs to be a hard stop. The pytest guard
    matches the one in is_firestore_configured() itself, for the same
    reason: this runs at collection-time import, before any test-level
    env var patching would apply.
    """
    if "pytest" in sys.modules:
        return
    if os.environ.get("REQUIRE_PERSISTENT_STORAGE") == "true" and not is_firestore_configured():
        raise RuntimeError(
            "REQUIRE_PERSISTENT_STORAGE=true but Firestore is not configured "
            "(FIRESTORE_EMULATOR_HOST/GOOGLE_CLOUD_PROJECT both unset). "
            "Refusing to start with silent in-memory storage."
        )


_require_persistent_storage_if_configured()

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
