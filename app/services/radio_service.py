"""
Radio Service - High-level service orchestrating all broadcast components
"""
import logging
from typing import Optional, Dict, Any

from ..core.runtime_manager import RuntimeManager
from ..core.show_planner import ShowPlanner, ShowPlan
from ..core.state_engine import StateEngine
from ..scheduler.scheduler_engine import SchedulerEngine
from ..streaming.stream_manager import StreamManager
from ..ai.llm_generator import initialize_llm_generator
from ..voice.tts_engine import initialize_tts_engine

logger = logging.getLogger(__name__)


class RadioService:
    """
    Main radio service
    Orchestrates show planning, state management, broadcast control, and scheduling
    """

    def __init__(self):
        """Initialize radio service"""
        self.show_planner = ShowPlanner()
        self.state_engine = StateEngine(use_redis=True)
        self.scheduler_engine = SchedulerEngine()
        self.stream_manager = StreamManager()
        self.runtime_manager = RuntimeManager(
            state_engine=self.state_engine,
            scheduler_engine=self.scheduler_engine,
            stream_manager=self.stream_manager,
        )
        self.show_plans: Dict[str, ShowPlan] = {}
        self.logger = logging.getLogger(__name__)

    async def initialize(self, config: Dict[str, Any]):
        """
        Initialize service with configuration

        Args:
            config: Configuration dict with API keys, settings
        """
        llm_key = config.get("openai_api_key", "")
        llm_model = config.get("openai_model", "gpt-4-turbo")
        initialize_llm_generator(llm_key, llm_model)

        tts_key = config.get("elevenlabs_api_key", "")
        initialize_tts_engine(tts_key)

        self.logger.info("Radio service initialized")

    async def create_show_plan(
        self,
        duration_hours: float,
        show_name: str = "AI Radio Show",
        template: Optional[str] = None,
        primary_language: str = "english",
        target_audience: str = "general",
        theme: str = "contemporary",
    ) -> ShowPlan:
        """
        Create a new show plan and persist it

        Args:
            duration_hours: Duration in hours
            show_name: Name of the show
            template: Optional template
            primary_language: Primary language
            target_audience: Target audience
            theme: Show theme

        Returns:
            ShowPlan: Generated show plan
        """
        duration_seconds = int(duration_hours * 3600)
        show_plan = self.show_planner.generate_show_plan(
            duration_seconds=duration_seconds,
            show_name=show_name,
            template=template,
            primary_language=primary_language,
            target_audience=target_audience,
            theme=theme,
        )

        self.show_plans[show_plan.show_id] = show_plan
        await self.state_engine.save_show_plan(show_plan)
        self.logger.info(f"Created show plan: {show_plan.show_id}")
        return show_plan

    async def get_show_plan(self, show_id: str) -> Optional[ShowPlan]:
        """Retrieve a saved show plan"""
        if show_id in self.show_plans:
            return self.show_plans[show_id]
        return await self.state_engine.load_show_plan(show_id)

    async def start_show(self, show_id: str, event_callback=None) -> Optional[str]:
        """
        Start a show immediately from an existing plan

        Args:
            show_id: Show plan identifier
            event_callback: Optional async callback for runtime events

        Returns:
            Optional[str]: Started show ID or None if not found
        """
        show_plan = await self.get_show_plan(show_id)
        if not show_plan:
            return None

        return await self.runtime_manager.start_show(show_plan)

    async def schedule_show(self, show_name: str, duration_hours: float, start_time, template: Optional[str] = None,
                            primary_language: str = "english", target_audience: str = "general", theme: str = "contemporary") -> str:
        """
        Create and schedule a show for a future time.
        """
        show_plan = await self.create_show_plan(
            duration_hours=duration_hours,
            show_name=show_name,
            template=template,
            primary_language=primary_language,
            target_audience=target_audience,
            theme=theme,
        )
        return await self.runtime_manager.schedule_show(show_plan, start_time)

    async def stop_show(self, show_id: str) -> bool:
        """Stop an active or scheduled show"""
        return await self.runtime_manager.stop_show(show_id)

    async def pause_show(self, show_id: str) -> bool:
        """Pause an active show"""
        return await self.runtime_manager.pause_show(show_id)

    async def resume_show(self, show_id: str) -> bool:
        """Resume a paused show"""
        return await self.runtime_manager.resume_show(show_id)

    async def get_show_state(self, show_id: str) -> Optional[Dict[str, Any]]:
        """Get current or persisted show state"""
        return await self.runtime_manager.get_show_state(show_id)

    async def get_show_history(self, show_id: str) -> Optional[Dict[str, Any]]:
        """Get historical state of a show"""
        return await self.runtime_manager.get_show_history(show_id)

    async def list_active_shows(self) -> Dict[str, Any]:
        """List currently active shows"""
        return await self.runtime_manager.list_active_shows()


# Global service instance
_radio_service: Optional[RadioService] = None


def get_radio_service() -> RadioService:
    """Get or create radio service"""
    global _radio_service
    if _radio_service is None:
        _radio_service = RadioService()
    return _radio_service


def initialize_radio_service(config: Dict[str, Any]) -> RadioService:
    """Initialize radio service"""
    global _radio_service
    _radio_service = RadioService()
    return _radio_service
