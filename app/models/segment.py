from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class SegmentType(str, Enum):
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
    ENERGETIC = "energetic"
    CALM = "calm"
    HUMOROUS = "humorous"
    SERIOUS = "serious"
    INFORMATIVE = "informative"
    UPLIFTING = "uplifting"
    MYSTERIOUS = "mysterious"


@dataclass
class Segment:
    segment_id: str
    segment_type: SegmentType
    title: str
    duration: int
    mood: Mood
    language: str = "english"
    priority: int = 1
    is_flexible: bool = False
    optional: bool = False
    requires_context: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["segment_type"] = self.segment_type.value
        data["mood"] = self.mood.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Segment":
        data_copy = data.copy()
        data_copy["segment_type"] = SegmentType(data_copy["segment_type"])
        data_copy["mood"] = Mood(data_copy["mood"])
        return cls(**data_copy)
