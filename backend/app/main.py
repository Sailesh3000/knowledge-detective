from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application lifespan — start local file watcher on boot
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: launch the local file-system watcher daemon."""
    try:
        from app.ingestion.watcher import LocalFolderWatcher
        watcher = LocalFolderWatcher()
        watcher.start(settings.TEST_DATA_DIR)
        logger.info(f"Local file watcher started on: {settings.TEST_DATA_DIR}")
    except Exception as exc:
        logger.warning(f"File watcher could not start (non-fatal): {exc}")
    yield  # application runs here
    # No explicit teardown needed; watcher thread is daemonized

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Knowledge Detective — multi-source ingestion, hybrid retrieval, and reasoning agent.",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "config": {
            "fireworks_model": settings.FIREWORKS_MODEL,
            "qdrant_host": settings.QDRANT_HOST,
            "neo4j_uri": settings.NEO4J_URI
        }
    }

# Register API Routers
from app.api.query import router as query_router
from app.api.timeline import router as timeline_router
from app.api.graph import router as graph_router
from app.api.demo import router as demo_router

app.include_router(query_router, prefix="/api", tags=["Query"])
app.include_router(timeline_router, prefix="/api", tags=["Timeline"])
app.include_router(graph_router, prefix="/api", tags=["Graph"])
app.include_router(demo_router, prefix="/api", tags=["Demo"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
