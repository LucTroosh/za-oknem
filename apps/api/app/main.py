from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import air, health, weather
from app.config import settings

app = FastAPI(title="Za Oknem API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(air.router, prefix="/api/v1")
app.include_router(weather.router, prefix="/api/v1")
