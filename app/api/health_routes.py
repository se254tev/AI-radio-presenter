"""
Enhanced health and monitoring endpoints
"""
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/detailed")
async def detailed_health() -> dict[str, Any]:
    """Detailed system health check with resource usage"""
    if not psutil:
        return {
            "status": "degraded",
            "error": "psutil is not installed",
            "timestamp": datetime.utcnow().isoformat(),
        }

    try:
        process = psutil.Process()
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / (1024 * 1024),
                "memory_percent": memory_percent,
                "threads": process.num_threads(),
            },
            "services": {
                "ai_dj": "operational",
                "tts": "operational",
                "queue": "operational",
                "websocket": "operational",
            },
            "uptime_seconds": process.create_time(),
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Kubernetes/Render readiness probe"""
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, Any]:
    """Kubernetes/Render liveness probe"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics/queue")
async def queue_metrics() -> dict[str, Any]:
    """Queue metrics endpoint"""
    return {
        "queue_size": 0,
        "max_size": 500,
        "current_track": None,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics/listeners")
async def listener_metrics() -> dict[str, Any]:
    """Listener metrics endpoint"""
    return {
        "active_listeners": 0,
        "peak_listeners": 0,
        "total_sessions": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics/ai")
async def ai_metrics() -> dict[str, Any]:
    """AI DJ metrics endpoint"""
    return {
        "ai_status": "operational",
        "model": "gpt-4-turbo",
        "last_generation": None,
        "generation_count": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/databases")
async def database_health(request: Request) -> dict[str, Any]:
    """Database connectivity health check"""
    app = request.app
    
    database_status = {
        "postgres": "unavailable",
        "mongodb": "unavailable",
        "redis": "unavailable",
    }
    
    # Check Postgres
    try:
        if hasattr(app.state, 'postgres') and app.state.postgres:
            await app.state.postgres.fetchrow("SELECT 1")
            database_status["postgres"] = "connected"
    except Exception as e:
        logger.warning(f"Postgres health check failed: {e}")
        database_status["postgres"] = "error"
    
    # Check MongoDB
    try:
        if hasattr(app.state, 'mongo') and app.state.mongo:
            is_healthy = await app.state.mongo.health_check()
            database_status["mongodb"] = "connected" if is_healthy else "unhealthy"
    except Exception as e:
        logger.warning(f"MongoDB health check failed: {e}")
        database_status["mongodb"] = "error"
    
    # Check Redis
    try:
        if hasattr(app.state, 'redis') and app.state.redis:
            is_healthy = await app.state.redis.ping()
            database_status["redis"] = "connected" if is_healthy else "unhealthy"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        database_status["redis"] = "error"
    
    return {
        "status": "healthy" if database_status.get("mongodb") in ["connected", "unavailable"] else "degraded",
        "databases": database_status,
        "timestamp": datetime.utcnow().isoformat(),
    }
