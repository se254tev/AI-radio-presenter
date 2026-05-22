"""
Show Planner - Pre-Execution Layer
Generates deterministic, structured show plans with segments, timing, and metadata
"""
import json
import logging
import uuid
from dataclasses import dataclass, asdict, field
from typing import Any
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class SegmentType(str, Enum):
    """Types of broadcast segments"""
    INTRO = "intro"
    NEWS = "news"
    MUSIC_BLOCK = "music_block"
    TALK_SEGMENT = "talk_segment"
    LISTENER_INTERACTION = "listener_interaction"
    AD_BREAK = "ad_break"
    WEATHER = "weather"
    SPORTS_UPDATE = "sports_update"
    JOKE_BREAK = "joke_break"
    FILLER = "filler"
    OUTRO = "outro"


class Mood(str, Enum):
    """Segment mood indicators"""
    ENERGETIC = "energetic"
    CALM = "calm"
    HUMOROUS = "humorous"
    SERIOUS = "serious"
    INFORMATIVE = "informative"
    UPLIFTING = "uplifting"
    MYSTERIOUS = "mysterious"


@dataclass
class Segment:
    """Individual broadcast segment definition"""
    segment_id: str
    segment_type: SegmentType
    title: str
    duration: int  # seconds
    mood: Mood
    language: str = "english"  # english, swahili, mixed
    priority: int = 1  # 1=high, 10=low (for flexible segments)
    is_flexible: bool = False  # Can be shortened/extended
    optional: bool = False  # Can be skipped
    requires_context: list[str] = field(default_factory=list)  # e.g., ["weather", "news"]
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['segment_type'] = self.segment_type.value
        data['mood'] = self.mood.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Segment':
        data_copy = data.copy()
        data_copy['segment_type'] = SegmentType(data_copy['segment_type'])
        data_copy['mood'] = Mood(data_copy['mood'])
        return cls(**data_copy)


@dataclass
class ShowPlan:
    """
    Complete show plan - deterministic and reproducible
    Generated before broadcast execution
    """
    show_id: str
    show_name: str
    total_duration: int  # seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    planned_start_time: datetime | None = None
    
    # Segments
    segments: list[Segment] = field(default_factory=list)
    
    # Configuration
    primary_language: str = "english"
    secondary_language: str = "swahili"
    code_switching_enabled: bool = True
    
    # Metadata
    target_audience: str = ""
    theme: str = ""
    host_personality: str = "friendly, knowledgeable, energetic"
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Execution hints
    buffer_seconds: int = 30  # Extra buffer for transitions
    version: str = "1.0"
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['planned_start_time'] = self.planned_start_time.isoformat() if self.planned_start_time else None
        data['segments'] = [s.to_dict() for s in self.segments]
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ShowPlan':
        """Reconstruct from dict"""
        data_copy = data.copy()
        data_copy['created_at'] = datetime.fromisoformat(data_copy['created_at'])
        if data_copy.get('planned_start_time'):
            data_copy['planned_start_time'] = datetime.fromisoformat(data_copy['planned_start_time'])
        data_copy['segments'] = [Segment.from_dict(s) for s in data_copy.get('segments', [])]
        return cls(**data_copy)
    
    def to_json(self, indent: int = 2) -> str:
        """Export to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save_to_file(self, filepath: str):
        """Save plan to JSON file"""
        with open(filepath, 'w') as f:
            f.write(self.to_json())
        logger.info(f"Show plan saved to {filepath}")
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'ShowPlan':
        """Load plan from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        logger.info(f"Show plan loaded from {filepath}")
        return cls.from_dict(data)
    
    def total_segment_duration(self) -> int:
        """Calculate total segment duration"""
        return sum(s.duration for s in self.segments)
    
    def get_segment_by_index(self, index: int) -> Segment | None:
        """Get segment by index"""
        if 0 <= index < len(self.segments):
            return self.segments[index]
        return None
    
    def get_segments_by_type(self, segment_type: SegmentType) -> list[Segment]:
        """Get all segments of a specific type"""
        return [s for s in self.segments if s.segment_type == segment_type]


class ShowPlanner:
    """
    Show Planning Engine
    Generates deterministic, structured show plans before execution
    """
    
    # Template configurations
    SHORT_SHOW_TEMPLATES = {
        "1_hour": {
            "segments": [
                {"type": SegmentType.INTRO, "duration": 180, "mood": Mood.ENERGETIC},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 300, "mood": Mood.UPLIFTING},
                {"type": SegmentType.TALK_SEGMENT, "duration": 400, "mood": Mood.INFORMATIVE},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 300, "mood": Mood.UPLIFTING},
                {"type": SegmentType.OUTRO, "duration": 120, "mood": Mood.CALM},
            ]
        },
        "2_hour": {
            "segments": [
                {"type": SegmentType.INTRO, "duration": 240, "mood": Mood.ENERGETIC},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 600, "mood": Mood.UPLIFTING},
                {"type": SegmentType.NEWS, "duration": 600, "mood": Mood.INFORMATIVE},
                {"type": SegmentType.TALK_SEGMENT, "duration": 900, "mood": Mood.HUMOROUS},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 600, "mood": Mood.UPLIFTING},
                {"type": SegmentType.LISTENER_INTERACTION, "duration": 480, "mood": Mood.ENERGETIC},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 300, "mood": Mood.CALM},
                {"type": SegmentType.OUTRO, "duration": 180, "mood": Mood.CALM},
            ]
        },
        "3_hour": {
            "segments": [
                {"type": SegmentType.INTRO, "duration": 300, "mood": Mood.ENERGETIC},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 600, "mood": Mood.UPLIFTING},
                {"type": SegmentType.NEWS, "duration": 480, "mood": Mood.INFORMATIVE},
                {"type": SegmentType.AD_BREAK, "duration": 120, "mood": Mood.CALM},
                {"type": SegmentType.TALK_SEGMENT, "duration": 1200, "mood": Mood.HUMOROUS},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 600, "mood": Mood.UPLIFTING},
                {"type": SegmentType.WEATHER, "duration": 300, "mood": Mood.INFORMATIVE},
                {"type": SegmentType.LISTENER_INTERACTION, "duration": 600, "mood": Mood.ENERGETIC},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 600, "mood": Mood.CALM},
                {"type": SegmentType.JOKE_BREAK, "duration": 240, "mood": Mood.HUMOROUS},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 300, "mood": Mood.CALM},
                {"type": SegmentType.OUTRO, "duration": 240, "mood": Mood.CALM},
            ]
        },
        "6_hour": {
            "segments": [
                {"type": SegmentType.INTRO, "duration": 300, "mood": Mood.ENERGETIC},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 900, "mood": Mood.UPLIFTING},
                {"type": SegmentType.NEWS, "duration": 600, "mood": Mood.INFORMATIVE},
                {"type": SegmentType.TALK_SEGMENT, "duration": 1200, "mood": Mood.HUMOROUS},
                {"type": SegmentType.AD_BREAK, "duration": 180, "mood": Mood.CALM},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 900, "mood": Mood.UPLIFTING},
                {"type": SegmentType.SPORTS_UPDATE, "duration": 600, "mood": Mood.ENERGETIC},
                {"type": SegmentType.LISTENER_INTERACTION, "duration": 900, "mood": Mood.ENERGETIC},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 600, "mood": Mood.CALM},
                {"type": SegmentType.WEATHER, "duration": 300, "mood": Mood.INFORMATIVE},
                {"type": SegmentType.TALK_SEGMENT, "duration": 1200, "mood": Mood.SERIOUS},
                {"type": SegmentType.AD_BREAK, "duration": 180, "mood": Mood.CALM},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 900, "mood": Mood.UPLIFTING},
                {"type": SegmentType.JOKE_BREAK, "duration": 300, "mood": Mood.HUMOROUS},
                {"type": SegmentType.LISTENER_INTERACTION, "duration": 600, "mood": Mood.ENERGETIC},
                {"type": SegmentType.MUSIC_BLOCK, "duration": 600, "mood": Mood.CALM},
                {"type": SegmentType.OUTRO, "duration": 300, "mood": Mood.CALM},
            ]
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_show_plan(
        self,
        duration_seconds: int,
        show_name: str = "AI Radio Show",
        template: str = None,
        primary_language: str = "english",
        target_audience: str = "general",
        theme: str = "contemporary",
    ) -> ShowPlan:
        """
        Generate a structured show plan
        
        Args:
            duration_seconds: Total show duration in seconds
            show_name: Name of the show
            template: Optional template name (e.g., "3_hour")
            primary_language: Primary broadcast language
            target_audience: Target audience description
            theme: Show theme/topic
        
        Returns:
            ShowPlan: Deterministic show plan ready for execution
        """
        show_id = f"show_{uuid.uuid4().hex[:12]}"
        
        # Determine template
        if not template:
            template = self._select_template(duration_seconds)
        
        # Get template segments
        if template not in self.SHORT_SHOW_TEMPLATES:
            template = "3_hour"  # Default fallback
        
        template_config = self.SHORT_SHOW_TEMPLATES[template]
        segments = []
        
        # Create segments from template
        for i, seg_config in enumerate(template_config["segments"]):
            segment = Segment(
                segment_id=f"seg_{show_id}_{i}",
                segment_type=seg_config["type"],
                title=f"{seg_config['type'].value.replace('_', ' ').title()} #{i+1}",
                duration=seg_config["duration"],
                mood=seg_config["mood"],
                language=primary_language,
                priority=i,
                is_flexible=(i > 0 and i < len(template_config["segments"]) - 1),  # Middle segments flexible
                optional=False,
                requires_context=self._get_context_requirements(seg_config["type"]),
                metadata={}
            )
            segments.append(segment)
        
        # Normalize duration
        segments = self._normalize_segments(segments, duration_seconds)
        
        # Create show plan
        show_plan = ShowPlan(
            show_id=show_id,
            show_name=show_name,
            total_duration=duration_seconds,
            created_at=datetime.utcnow(),
            segments=segments,
            primary_language=primary_language,
            secondary_language="swahili",
            code_switching_enabled=True,
            target_audience=target_audience,
            theme=theme,
            host_personality="friendly, knowledgeable, energetic, culturally aware",
            metadata={
                "template": template,
                "segment_count": len(segments),
                "total_segment_duration": sum(s.duration for s in segments),
            }
        )
        
        self.logger.info(
            f"Generated show plan: {show_name} ({duration_seconds}s) "
            f"with {len(segments)} segments from template {template}"
        )
        
        return show_plan
    
    def _select_template(self, duration_seconds: int) -> str:
        """Select appropriate template based on duration"""
        hours = duration_seconds / 3600
        
        if hours <= 1.5:
            return "1_hour"
        elif hours <= 2.5:
            return "2_hour"
        elif hours <= 4:
            return "3_hour"
        else:
            return "6_hour"
    
    def _normalize_segments(self, segments: list[Segment], total_duration: int) -> list[Segment]:
        """
        Normalize segment durations to fit total_duration
        Preserves relative proportions for most segments
        Adjusts flexible segments more aggressively
        """
        current_total = sum(s.duration for s in segments)
        
        if current_total == total_duration:
            return segments
        
        if current_total > total_duration:
            # Need to reduce - prioritize reducing flexible segments
            difference = current_total - total_duration
            for segment in segments:
                if segment.is_flexible and difference > 0:
                    reduction = min(difference, segment.duration - 60)  # Min 60 sec
                    segment.duration -= reduction
                    difference -= reduction
        else:
            # Need to expand
            difference = total_duration - current_total
            flexible_segments = [s for s in segments if s.is_flexible]
            if flexible_segments:
                per_segment = difference // len(flexible_segments)
                for segment in flexible_segments:
                    segment.duration += per_segment
        
        return segments
    
    def _get_context_requirements(self, segment_type: SegmentType) -> list[str]:
        """Get required context for segment type"""
        context_map = {
            SegmentType.NEWS: ["news_feed", "recent_events"],
            SegmentType.WEATHER: ["weather_data", "location"],
            SegmentType.SPORTS_UPDATE: ["sports_scores", "recent_games"],
            SegmentType.LISTENER_INTERACTION: ["listener_requests", "audience_mood"],
            SegmentType.TALK_SEGMENT: ["topic_research", "audience_interest"],
        }
        return context_map.get(segment_type, [])
    
    def save_plan(self, show_plan: ShowPlan, filepath: str = None) -> str:
        """Save show plan to file"""
        if not filepath:
            filepath = f"show_plans/{show_plan.show_id}.json"
        show_plan.save_to_file(filepath)
        return filepath


# Global planner instance
show_planner = ShowPlanner()
