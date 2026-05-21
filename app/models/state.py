import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class SegmentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"


class BroadcastStatus(str, Enum):
    CREATED = "created"
    SCHEDULED = "scheduled"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class AudienceMetrics:
    energy_level: float = 0.5
    sentiment: str = "neutral"
    engagement_rate: float = 0.5
    listener_count: int = 1000
    request_queue: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudienceMetrics":
        return cls(**data)


@dataclass
class SegmentExecution:
    segment_id: str
    segment_type: str
    title: str
    status: SegmentStatus = SegmentStatus.PENDING
    planned_duration: int = 0
    actual_duration: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    language: str = "english"
    mood: str = "neutral"
    content_hash: str = ""
    audio_url: Optional[str] = None
    notes: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["start_time"] = self.start_time.isoformat() if self.start_time else None
        data["end_time"] = self.end_time.isoformat() if self.end_time else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SegmentExecution":
        data_copy = data.copy()
        data_copy["status"] = SegmentStatus(data_copy.get("status", "pending"))
        if data_copy.get("start_time"):
            data_copy["start_time"] = datetime.fromisoformat(data_copy["start_time"])
        if data_copy.get("end_time"):
            data_copy["end_time"] = datetime.fromisoformat(data_copy["end_time"])
        return cls(**data_copy)


@dataclass
class ShowState:
    show_id: str
    show_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    planned_duration: int = 0
    scheduled_start_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: BroadcastStatus = BroadcastStatus.CREATED
    current_segment_index: int = -1
    segments_completed: int = 0
    total_segments: int = 0
    elapsed_time: int = 0
    remaining_time: int = 0
    paused_duration: int = 0
    segment_history: List[SegmentExecution] = field(default_factory=list)
    audience_metrics: AudienceMetrics = field(default_factory=AudienceMetrics)
    energy_level: float = 0.5
    humor_level: float = 0.3
    language_mix_level: float = 0.0
    primary_language: str = "english"
    secondary_language: str = "swahili"
    current_language: str = "english"
    version: int = 1
    last_updated: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["scheduled_start_time"] = self.scheduled_start_time.isoformat() if self.scheduled_start_time else None
        data["start_time"] = self.start_time.isoformat() if self.start_time else None
        data["end_time"] = self.end_time.isoformat() if self.end_time else None
        data["last_updated"] = self.last_updated.isoformat()
        data["audience_metrics"] = self.audience_metrics.to_dict()
        data["segment_history"] = [entry.to_dict() for entry in self.segment_history]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShowState":
        data_copy = data.copy()
        data_copy["status"] = BroadcastStatus(data_copy.get("status", "created"))
        data_copy["created_at"] = datetime.fromisoformat(data_copy["created_at"])
        if data_copy.get("scheduled_start_time"):
            data_copy["scheduled_start_time"] = datetime.fromisoformat(data_copy["scheduled_start_time"])
        if data_copy.get("start_time"):
            data_copy["start_time"] = datetime.fromisoformat(data_copy["start_time"])
        if data_copy.get("end_time"):
            data_copy["end_time"] = datetime.fromisoformat(data_copy["end_time"])
        data_copy["last_updated"] = datetime.fromisoformat(data_copy["last_updated"])
        data_copy["audience_metrics"] = AudienceMetrics.from_dict(data_copy.get("audience_metrics", {}))
        data_copy["segment_history"] = [SegmentExecution.from_dict(entry) for entry in data_copy.get("segment_history", [])]
        return cls(**data_copy)

    def update_timing(self, current_time: Optional[datetime] = None):
        if current_time is None:
            current_time = datetime.utcnow()
        if self.start_time:
            self.elapsed_time = int((current_time - self.start_time).total_seconds())
            self.remaining_time = max(0, self.planned_duration - self.elapsed_time)
        self.last_updated = current_time

    @property
    def is_active(self) -> bool:
        return self.status == BroadcastStatus.RUNNING

    def current_segment(self) -> Optional[SegmentExecution]:
        if 0 <= self.current_segment_index < len(self.segment_history):
            return self.segment_history[self.current_segment_index]
        return None

    def add_segment_record(self, record: SegmentExecution):
        self.segment_history.append(record)
        self.current_segment_index = len(self.segment_history) - 1
        self.total_segments = len(self.segment_history)

    def get_recent_context(self, lookback_segments: int = 3) -> List[SegmentExecution]:
        return self.segment_history[-lookback_segments:]

    def complete_current_segment(self):
        current = self.current_segment()
        if current and current.status == SegmentStatus.ACTIVE:
            current.status = SegmentStatus.COMPLETED
            current.end_time = datetime.utcnow()
            current.actual_duration = int((current.end_time - current.start_time).total_seconds()) if current.start_time else current.planned_duration
            self.segments_completed += 1

    def set_active_segment(self, record: SegmentExecution):
        self.add_segment_record(record)
        record.status = SegmentStatus.ACTIVE
        record.start_time = datetime.utcnow()
