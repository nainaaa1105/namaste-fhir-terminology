from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import get_settings
from api.logging_config import setup_logging
from api.middleware import RequestTimingMiddleware
from api.routes import health, expand, translate, bundle, analytics, claims, metadata, history
from api.routes.fhir import codesystem as fhir_codesystem
from api.routes.fhir import conceptmap as fhir_conceptmap
from api.routes.fhir import fhir_expand, fhir_translate, fhir_bundle
from api.dependencies import get_app_state
from db.session import init_db

settings = get_settings()
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to perform startup database initialization and state loading."""
    logger.info("Initializing AYUSH EMR Terminology Microservice...")
    try:
        init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to database on startup: {e}. Microservice starting with degraded DB connectivity.")
    
    # Initialize application state singletons
    try:
        state = get_app_state()
        state.init_hash_index()
        state.init_encoder(mock=True)
    except Exception as e:
        logger.warning(f"Could not initialize app state singletons: {e}")

    yield
    logger.info("Shutting down AYUSH EMR Terminology Microservice...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AYUSH EMR Terminology Microservice (NAMASTE, ICD-11-TM2, SNOMED-CT, NHCX)",
    lifespan=lifespan
)

# Middleware
app.add_middleware(RequestTimingMiddleware)

# CORS Configuration
# allow_origins covers explicitly listed origins (from ALLOWED_ORIGINS env var).
# allow_origin_regex covers all Vercel preview/production deployments (*.vercel.app)
# and the specific Render backend domain for health-check cross-service calls.
origins = settings.ALLOWED_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 4 — Cascading hybrid terminology routes
app.include_router(health.router)
app.include_router(metadata.router)
app.include_router(expand.router, prefix="/api")
app.include_router(translate.router, prefix="/api")
app.include_router(bundle.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(claims.router)
app.include_router(history.router, prefix="/api")

# Layer 2 — FHIR R4 terminology interoperability routes
app.include_router(fhir_codesystem.router)
app.include_router(fhir_conceptmap.router)
app.include_router(fhir_expand.router)
app.include_router(fhir_translate.router)
app.include_router(fhir_bundle.router)

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount frontend build dist if available for serving SPA directly via FastAPI
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/ui", include_in_schema=False)
    @app.get("/ui/{full_path:path}", include_in_schema=False)
    async def serve_spa_ui(full_path: str = ""):
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/")
def read_root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "documentation": "/docs",
        "health": "/health",
        "frontend_ui": "http://localhost:5173/"
    }
