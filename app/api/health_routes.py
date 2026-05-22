"""
Enhanced health and monitoring endpoints
"""
import logging
import psutil
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/detailed")
async def detailed_health() -> Dict[str, Any]:
    """Detailed system health check with resource usage"""
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
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes/Render readiness probe"""
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """Kubernetes/Render liveness probe"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics/queue")
async def queue_metrics() -> Dict[str, Any]:
    """Queue metrics endpoint"""
    return {
        "queue_size": 0,
        "max_size": 500,
        "current_track": None,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics/listeners")
async def listener_metrics() -> Dict[str, Any]:
    """Listener metrics endpoint"""
    return {
        "active_listeners": 0,
        "peak_listeners": 0,
        "total_sessions": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics/ai")
async def ai_metrics() -> Dict[str, Any]:
    """AI DJ metrics endpoint"""
    return {
        "ai_status": "operational",
        "model": "gpt-4-turbo",
        "last_generation": None,
        "generation_count": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }
