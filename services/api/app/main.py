from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.cases import router as cases_router
from app.api.routes.health import router as health_router
from app.api.routes.hints import router as hints_router
from app.api.routes.players import router as players_router
from app.api.routes.scores import router as scores_router

app = FastAPI(title="Tiny Detective API")

# Permissive for local development so the Flutter web app (a different
# origin/port) can call the API from the browser. Tighten to the real
# frontend origin before any real deployment (Phase 8).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(cases_router)
app.include_router(hints_router)
app.include_router(players_router)
app.include_router(scores_router)
app.include_router(admin_router)
