import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import air, alerts, dashboard, health, hydro, pollen, weather
from app.config import settings
from app.middleware import RequestLoggingMiddleware

# uvicorn's own logging config doesn't attach a handler to the root logger, so
# without this, app.request's INFO lines would be silently dropped (root falls
# back to WARNING-only lastResort handler).
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Za Oknem API")

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(air.router, prefix="/api/v1")
app.include_router(weather.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(hydro.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(pollen.router, prefix="/api/v1")
