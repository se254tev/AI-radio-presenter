"""
Main FastAPI Application
Entry point for AI Radio Presenter system
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.logging import configure_logging
from app.config.settings import CONFIG
from app.api.routes import router
from app.api.show_routes import router as show_router
from app.services.radio_service import initialize_radio_service

# Configure logging
configure_logging(CONFIG.broadcast.log_level)
logger = __import__("logging").getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management
    Handles startup and shutdown
    """
    # Startup
    logger.info("Starting AI Radio Presenter System")
    
    try:
        service = initialize_radio_service({
            "openai_api_key": CONFIG.api.openai_key,
            "openai_model": CONFIG.api.openai_model,
            "elevenlabs_api_key": CONFIG.api.elevenlabs_key,
        })
        await service.initialize({
            "openai_api_key": CONFIG.api.openai_key,
            "openai_model": CONFIG.api.openai_model,
            "elevenlabs_api_key": CONFIG.api.elevenlabs_key,
        })
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Radio Presenter System")
    # Add cleanup code here if needed


# Create FastAPI application
app = FastAPI(
    title=CONFIG.app_name,
    description="Production-Ready Autonomous AI Radio Presenter System",
    version=CONFIG.version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routes
app.include_router(router)
app.include_router(show_router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": CONFIG.app_name,
        "version": CONFIG.version,
        "status": "running",
        "docs": "/docs",
        "api_base": "/api/v1/radio/shows",
        "environment": CONFIG.environment,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=CONFIG.debug,
        log_level=CONFIG.broadcast.log_level.lower(),
    )
