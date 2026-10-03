import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    air,
    alerts,
    dashboard,
    devices,
    geo,
    health,
    hydro,
    neighborhood,
    places,
    pollen,
    pollen_calendar,
    weather,
)
from app.config import settings
from app.middleware import RequestLoggingMiddleware
from app.pollen_calendar import load_calendar

# uvicorn's own logging config doesn't attach a handler to the root logger, so
# without this, app.request's INFO lines would be silently dropped (root falls
# back to WARNING-only lastResort handler).
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    load_calendar()  # fail fast at startup if the reference data file is invalid (ADR-023)
    yield


app = FastAPI(title="Za Oknem API", lifespan=lifespan)


COORDINATE_PATHS = {"/api/v1/geo/resolve", "/api/v1/geo/locate"}  # bodies carry lat/lon (ADR-002)


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's default 422 echoes the rejected `input`. For /geo/resolve that is the
    user's coordinates, so strip it there (ADR-002); other routes keep the default shape."""
    errors = exc.errors()
    # /places: the search text is the user's query, not echoed either (ADR-029).
    if request.url.path in COORDINATE_PATHS or request.url.path.startswith("/api/v1/places"):
        errors = [{k: v for k, v in e.items() if k not in ("input", "ctx")} for e in errors]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


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
app.include_router(devices.router, prefix="/api/v1")
app.include_router(geo.router, prefix="/api/v1")
app.include_router(neighborhood.router, prefix="/api/v1")
app.include_router(places.router, prefix="/api/v1")
app.include_router(pollen.router, prefix="/api/v1")
app.include_router(pollen_calendar.router, prefix="/api/v1")
