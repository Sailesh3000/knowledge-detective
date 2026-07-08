from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Knowledge Detective — multi-source ingestion, hybrid retrieval, and reasoning agent.",
    version="0.1.0",
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
            "ollama_model": settings.OLLAMA_MODEL,
            "qdrant_host": settings.QDRANT_HOST,
            "neo4j_uri": settings.NEO4J_URI
        }
    }

# We'll register the routers here as they are implemented.
# from app.api import ingest, query, timeline, graph
# app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingestion"])
# app.include_router(query.router, prefix="/api", tags=["Query"])
# app.include_router(timeline.router, prefix="/api", tags=["Timeline"])
# app.include_router(graph.router, prefix="/api", tags=["Graph"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
