from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.assets import router as assets_router
from app.api.measurements import router as measurements_router
from app.api.weather import router as weather_router
from app.api.grid import router as grid_router
from app.api.workflow import router as workflow_router
from app.api.forecasting import router as forecasting_router
from app.api.demand_forecasting import router as demand_forecasting_router
from app.api.battery import router as battery_router
from app.api.alerts import router as alerts_router
from app.api.reports import router as reports_router
from app.api.historical_energy import router as historical_energy_router
from app.db.database import Base, engine
from app.db import models as db_models


app = FastAPI(
    title="Renewable Energy AI",
    description="Renewable Energy Generation Forecasting and Grid Coordination System",
    version="1.0.0",
)

# Single combined CORS middleware with wildcard regex for all Vercel domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    assets_router,
    measurements_router,
    weather_router,
    grid_router,
    workflow_router,
    forecasting_router,
    demand_forecasting_router,
    battery_router,
    alerts_router,
    reports_router,
    historical_energy_router,
):
    app.include_router(router)


@app.on_event("startup")
def initialize_database_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "running", "application": "Renewable Energy AI"}


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Renewable Energy Forecasting and Grid Coordination System",
        "docs": "/docs",
        "health": "/health",
    }