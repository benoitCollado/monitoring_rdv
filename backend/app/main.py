import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import catalog, companies, monitoring
from app.core.config import get_settings
from app.services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.scheduler_enabled:
        await start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="Odoo Link Monitor",
    description=(
        "Génère les liens de prise de RDV Odoo (boutique x type x conseiller) "
        "et vérifie chaque jour qu'ils répondent."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(catalog.router)
app.include_router(monitoring.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config", tags=["health"])
async def config() -> dict[str, bool]:
    """Lets the frontend know whether it must ask for an API key."""
    return {"auth_required": bool(settings.api_key)}
