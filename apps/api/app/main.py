import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import air, alerts, dashboard, devices, geo, health, hydro, pollen, weather
from app.config import settings
from app.middleware import RequestLoggingMiddleware

# uvicorn's own logging config doesn't attach a handler to the root logger, so
# without this, app.request's INFO lines would be silently dropped (root falls
# back to WARNING-only lastResort handler).
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Za Oknem API")


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's default 422 echoes the rejected `input`. For /geo/resolve that is the
    user's coordinates, so strip it there (ADR-002); other routes keep the default shape."""
    errors = exc.errors()
    if request.url.path == "/api/v1/geo/resolve":
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
app.include_router(pollen.router, prefix="/api/v1")
