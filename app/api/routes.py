"""
FastAPI Routes - REST API for AI Radio System
Provides endpoints for managing shows and broadcasts
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


from ..services.radio_service import get_radio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/radio", tags=["radio"])


class CreateShowRequest(BaseModel):
    """Request to create a new show plan"""
    duration_hours: float
    show_name: str = "AI Radio Show"
    template: str | None = None
    primary_language: str = "english"
    target_audience: str = "general"
    theme: str = "contemporary"


class ShowPlanResponse(BaseModel):
    """Show plan response"""
    show_id: str
    show_name: str
    total_duration: int
    segments_count: int
    primary_language: str


class BroadcastStatusResponse(BaseModel):
    """Broadcast status response"""
    show_id: str
    show_name: str
    status: str
    elapsed_time: int
    remaining_time: int
    current_segment_index: int
    total_segments: int
    segments_completed: int
    energy_level: float


class ControlAction(BaseModel):
    """Broadcast control action"""
    action: str


@router.post("/show/create", response_model=ShowPlanResponse)
async def create_show(request: CreateShowRequest) -> ShowPlanResponse:
    service = get_radio_service()

    try:
        show_plan = service.create_show_plan(
            duration_hours=request.duration_hours,
            show_name=request.show_name,
            template=request.template,
            primary_language=request.primary_language,
            target_audience=request.target_audience,
            theme=request.theme,
        )

        return ShowPlanResponse(
            show_id=show_plan.show_id,
            show_name=show_plan.show_name,
            total_duration=show_plan.total_duration,
            segments_count=len(show_plan.segments),
            primary_language=show_plan.primary_language,
        )

    except Exception as exc:
        logger.error(f"Error creating show: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/show/{show_id}/start")
async def start_broadcast(show_id: str):
    service = get_radio_service()

    try:
        broadcast = await service.start_broadcast(show_id)
        if broadcast is None:
            raise HTTPException(status_code=404, detail=f"Show plan {show_id} not found")

        return {
            "status": "started",
            "show_id": show_id,
            "message": "Broadcast started - running autonomously",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error starting broadcast: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/show/{show_id}/status", response_model=BroadcastStatusResponse)
async def get_broadcast_status(show_id: str):
    service = get_radio_service()

    try:
        status = await service.get_broadcast_status(show_id)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])

        return BroadcastStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting status: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/show/{show_id}/control")
async def control_broadcast(show_id: str, action: ControlAction):
    service = get_radio_service()

    try:
        if action.action == "pause":
            success = await service.pause_broadcast(show_id)
        elif action.action == "resume":
            success = await service.resume_broadcast(show_id)
        elif action.action == "stop":
            success = await service.stop_broadcast(show_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")

        if not success:
            raise HTTPException(status_code=404, detail=f"Broadcast {show_id} not found or not active")

        return {
            "status": "success",
            "action": action.action,
            "show_id": show_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error controlling broadcast: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/broadcasts")
async def list_broadcasts():
    service = get_radio_service()

    try:
        broadcasts = await service.get_all_broadcasts()
        return {"broadcasts": broadcasts}

    except Exception as exc:
        logger.error(f"Error listing broadcasts: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AI Radio Presenter",
        "version": "1.0.0",
    }
