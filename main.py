"""
Main FastAPI Application - Production AI Radio Presenter System
Entry point with full async lifecycle management
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Core imports
from app.config.logging import configure_logging
from app.config.settings import CONFIG
from app.api.routes import router as legacy_router
from app.api.show_routes import router as show_router
from app.api.v1_routes import router as v1_router
from app.api.health_routes import router as health_router
from app.services.radio_service import initialize_radio_service
from app.services.ai_dj import AIRadioHost
from app.services.tts_engine import TTSEngine
from app.services.music_queue import MusicQueue
from app.streaming.websocket import handle_ws_connection, ws_manager

# Configure logging
configure_logging(CONFIG.broadcast.log_level)
logger = logging.getLogger(__name__)

# ============= Global Service Instances =============
ai_dj = AIRadioHost(
    openai_api_key=CONFIG.api.openai_key,
    model=CONFIG.api.openai_model,
    temperature=CONFIG.api.openai_temperature,
)

tts_engine = TTSEngine(
    elevenlabs_api_key=CONFIG.api.elevenlabs_key,
)

music_queue = MusicQueue(
    redis_client=None,  # Redis client initialized in lifespan if available
    max_queue_size=500,
)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management (startup & shutdown)"""
    logger.info("=" * 60)
    logger.info("Starting AI Radio Presenter System")
    logger.info(f"Environment: {CONFIG.environment}")
    logger.info(f"Debug Mode: {CONFIG.debug}")
    logger.info("=" * 60)
    
    app.state.ready = False

    # Validate required environment variables
    missing_vars = []
    if not CONFIG.api.openai_key:
        missing_vars.append("OPENAI_API_KEY")
    if not CONFIG.api.elevenlabs_key:
        missing_vars.append("ELEVENLABS_API_KEY")

    if missing_vars:
        logger.warning(
            "⚠️  Missing environment variables: %s",
            ", ".join(missing_vars),
        )
        logger.warning("AI features will be degraded; using fallback providers")

    try:
        # Initialize AI DJ
        logger.info("Initializing AI DJ service...")
        await ai_dj.initialize()

        # Initialize TTS Engine
        logger.info("Initializing TTS engine...")
        await tts_engine.initialize()

        # Initialize Music Queue
        logger.info("Initializing music queue...")
        await music_queue.initialize()

        # Legacy radio service initialization
        logger.info("Initializing legacy radio service...")
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

        # Store services in app state for API endpoints
        app.state.ai_dj = ai_dj
        app.state.tts_engine = tts_engine
        app.state.music_queue = music_queue
        app.state.ws_manager = ws_manager
        app.state.radio_service = service

        app.state.ready = True
        logger.info("✅ All services initialized successfully")
        logger.info("=" * 60)

    except Exception as exc:
        logger.error("❌ Startup initialization failed", exc_info=True)
        if CONFIG.environment == "production":
            sys.exit(1)  # Exit on production startup failure
        raise

    yield

    # Shutdown phase
    logger.info("=" * 60)
    logger.info("Shutting down AI Radio Presenter System")
    logger.info("=" * 60)
    app.state.ready = False


app = FastAPI(
    title=CONFIG.app_name,
    description="Production-Ready Autonomous AI Radio Presenter System",
    version=CONFIG.version,
    docs_url="/docs" if not CONFIG.debug else "/docs",
    redoc_url="/redoc" if not CONFIG.debug else "/redoc",
    openapi_url="/openapi.json" if not CONFIG.debug else "/openapi.json",
    lifespan=lifespan,
)

# ============= CORS Configuration =============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Route Registration =============
# Health and monitoring
app.include_router(health_router)

# Production API v1
app.include_router(v1_router)

# Legacy routes (for backward compatibility)
app.include_router(legacy_router)
app.include_router(show_router)

# ============= WebSocket Endpoint =============
@app.websocket("/ws/radio")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time radio streaming"""
    await handle_ws_connection(websocket)


# ============= Global Exception Handler =============
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
        } if CONFIG.debug else {"detail": "Internal server error"},
    )


# ============= Root Endpoints =============
@app.get("/")
async def root():
    """Root endpoint with service metadata"""
    return {
        "service": CONFIG.app_name,
        "version": CONFIG.version,
        "status": "running" if app.state.ready else "initializing",
        "environment": CONFIG.environment,
        "endpoints": {
            "health": "/health",
            "health_detailed": "/health/detailed",
            "api": "/api/v1",
            "docs": "/docs",
            "websocket": "/ws/radio",
        },
    }


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "ready": app.state.ready,
    }


@app.get("/status")
async def status():
    """Get current system status"""
    try:
        ai_status = await ai_dj.get_show_status() if hasattr(app.state, "ai_dj") else {}
        queue_status = await music_queue.get_status() if hasattr(app.state, "music_queue") else {}
        tts_status = await tts_engine.get_status() if hasattr(app.state, "tts_engine") else {}
        ws_status = await ws_manager.get_status() if hasattr(app.state, "ws_manager") else {}

        return {
            "app_ready": app.state.ready,
            "environment": CONFIG.environment,
            "services": {
                "ai_dj": ai_status,
                "music_queue": queue_status,
                "tts_engine": tts_status,
                "websocket": ws_status,
            },
        }
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return {
            "app_ready": app.state.ready,
            "environment": CONFIG.environment,
            "error": str(e),
        }


if __name__ == "__main__":
    import uvicorn

    # Get port from environment or use default
    port = int(os.getenv("PORT", "10000"))
    
    # Get host from environment or use localhost binding
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting uvicorn server on {host}:{port}")
    logger.info(f"Environment: {CONFIG.environment}")
    logger.info(f"Debug: {CONFIG.debug}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=CONFIG.debug and CONFIG.environment == "development",
        log_level=CONFIG.broadcast.log_level.lower(),
        workers=1 if CONFIG.debug else 4,
    )

