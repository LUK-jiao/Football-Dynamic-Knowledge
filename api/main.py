"""
FastAPI main application entry point.
Configures routers, middleware, and application lifecycle events.
"""

from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.logging import setup_logging
from api.routers import datasource, knowledge, retrieval, rag, feedback

# Initialize settings and logging
settings = get_settings()
setup_logging()

app = FastAPI(
    title="Football Knowledge Crawler API",
    description="动态大模型知识库系统（面向足球爱好者）",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(datasource.router, prefix="/api/v1/datasource", tags=["datasource"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(retrieval.router, prefix="/api/v1/retrieval", tags=["retrieval"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Football Knowledge Crawler API",
        "version": "0.1.0",
        "docs": "/api/docs",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    # TODO: Add actual health checks for dependencies
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event() -> None:
    """Application startup event."""
    # TODO: Initialize database connections, load models, etc.
    pass


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Application shutdown event."""
    # TODO: Close database connections, cleanup resources
    pass
