"""
Main FastAPI Application
Entry point for AI Radio Presenter system
"""
import logging
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
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Radio Presenter System")
    app.state.ready = False

    missing_vars = []
    if not CONFIG.api.openai_key:
        missing_vars.append("OPENAI_API_KEY")
    if not CONFIG.api.elevenlabs_key:
        missing_vars.append("ELEVENLABS_API_KEY")

    if missing_vars:
        logger.warning(
            "Missing environment variables; AI functionality may be degraded: %s",
            ", ".join(missing_vars),
        )

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
        app.state.ready = True
        logger.info("Services initialized successfully")
    except Exception as exc:
        logger.exception("Startup initialization failed")
        raise

    yield

    logger.info("Shutting down AI Radio Presenter System")
    app.state.ready = False


app = FastAPI(
    title=CONFIG.app_name,
    description="Production-Ready Autonomous AI Radio Presenter System",
    version=CONFIG.version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(show_router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    return {
        "service": CONFIG.app_name,
        "version": CONFIG.version,
        "status": "running",
        "health": "/health",
        "api_base": "/api/v1/radio/shows",
        "environment": CONFIG.environment,
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=10000,
        reload=CONFIG.debug,
        log_level=CONFIG.broadcast.log_level.lower(),
    )
