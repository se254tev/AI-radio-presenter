import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

from .segment import Segment


@dataclass
class ShowPlan:
    show_id: str
    show_name: str
    total_duration: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    planned_start_time: Optional[datetime] = None
    segments: List[Segment] = field(default_factory=list)
    primary_language: str = "english"
    secondary_language: str = "swahili"
    code_switching_enabled: bool = True
    target_audience: str = "general"
    theme: str = "contemporary"
    host_personality: str = "friendly, knowledgeable, energetic"
    metadata: Dict[str, Any] = field(default_factory=dict)
    buffer_seconds: int = 30
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["planned_start_time"] = self.planned_start_time.isoformat() if self.planned_start_time else None
        data["segments"] = [segment.to_dict() for segment in self.segments]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShowPlan":
        data_copy = data.copy()
        data_copy["created_at"] = datetime.fromisoformat(data_copy["created_at"])
        if data_copy.get("planned_start_time"):
            data_copy["planned_start_time"] = datetime.fromisoformat(data_copy["planned_start_time"])
        data_copy["segments"] = [Segment.from_dict(seg) for seg in data_copy.get("segments", [])]
        return cls(**data_copy)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as handle:
            handle.write(self.to_json())

    @classmethod
    def load_from_file(cls, filepath: str) -> "ShowPlan":
        with open(filepath, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return cls.from_dict(data)

    def total_segment_duration(self) -> int:
        return sum(segment.duration for segment in self.segments)

    def get_segment_by_index(self, index: int) -> Optional[Segment]:
        if 0 <= index < len(self.segments):
            return self.segments[index]
        return None

    def get_segments_by_type(self, segment_type: str) -> List[Segment]:
        return [segment for segment in self.segments if segment.segment_type.value == segment_type]
