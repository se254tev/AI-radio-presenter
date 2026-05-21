import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.radio_service import get_radio_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/radio/shows", tags=["shows"])


class ShowControlRequest(BaseModel):
    duration_hours: Optional[float] = Field(None, gt=0)
    show_name: Optional[str] = "AI Radio Show"
    template: Optional[str] = None
    primary_language: Optional[str] = "english"
    target_audience: Optional[str] = "general"
    theme: Optional[str] = "contemporary"
    scheduled_start: Optional[datetime] = None


class ControlAction(BaseModel):
    action: str


@router.post("/start")
async def start_show(request: ShowControlRequest):
    service = get_radio_service()
    try:
        if request.duration_hours is None:
            raise HTTPException(status_code=400, detail="duration_hours is required")

        if request.scheduled_start:
            show_id = await service.schedule_show(
                show_name=request.show_name,
                duration_hours=request.duration_hours,
                start_time=request.scheduled_start,
                template=request.template,
                primary_language=request.primary_language,
                target_audience=request.target_audience,
                theme=request.theme,
            )
            return {
                "status": "scheduled",
                "show_id": show_id,
                "scheduled_start": request.scheduled_start.isoformat(),
            }

        show_plan = await service.create_show_plan(
            duration_hours=request.duration_hours,
            show_name=request.show_name,
            template=request.template,
            primary_language=request.primary_language,
            target_audience=request.target_audience,
            theme=request.theme,
        )

        show_id = await service.start_show(show_plan.show_id)
        return {
            "status": "started",
            "show_id": show_id,
        }
    except Exception as exc:
        logger.error(f"Error starting show: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/stop/{show_id}")
async def stop_show(show_id: str):
    service = get_radio_service()
    if not await service.stop_show(show_id):
        raise HTTPException(status_code=404, detail="Show not found")
    return {"status": "stopped", "show_id": show_id}


@router.post("/pause/{show_id}")
async def pause_show(show_id: str):
    service = get_radio_service()
    if not await service.pause_show(show_id):
        raise HTTPException(status_code=404, detail="Show not active")
    return {"status": "paused", "show_id": show_id}


@router.post("/resume/{show_id}")
async def resume_show(show_id: str):
    service = get_radio_service()
    if not await service.resume_show(show_id):
        raise HTTPException(status_code=404, detail="Show not active")
    return {"status": "running", "show_id": show_id}


@router.get("/state/{show_id}")
async def get_show_state(show_id: str):
    service = get_radio_service()
    state = await service.get_show_state(show_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Show not found")
    return state


@router.get("/history/{show_id}")
async def get_show_history(show_id: str):
    service = get_radio_service()
    history = await service.get_show_history(show_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Show not found")
    return history
