from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SpeechTestRequest(BaseModel):
    patient_id: str = Field(min_length=1, examples=["NW-1024"])
    test_id: str = Field(min_length=1, examples=["speech-2026-08-21-001"])
    timestamp: datetime


class FeatureDict(BaseModel):
    """Features extracted or calculated for a speech test."""

    speech_activity_rate: float
    average_pause_duration: float
    long_pause_count: int
    estimated_speech_duration: float


class SpeechTestResult(BaseModel):
    patient_id: str
    test_id: str
    status: Literal["stable", "attention", "significant_change", "baseline_establishing"]
    deviation_score: float = Field(ge=0, le=1)
    audio_duration: float = Field(ge=0)
    estimated_speech_duration: float = Field(ge=0)
    speech_rate: int = Field(ge=0)
    pause_score: float = Field(ge=0, le=1)
    average_pause_duration: float = Field(ge=0)
    long_pause_count: int = Field(ge=0)
    transcription_score: float = Field(ge=0, le=1)
    message: str
    monitoring_message: str = Field(default="")
    audio_received: bool
    audio_filename: str
    audio_content_type: str
    audio_size_bytes: int = Field(gt=0)
    # New baseline fields
    baseline_available: bool = Field(default=False)
    baseline_test_count: int = Field(default=0, ge=0)
    current_features: Optional[FeatureDict] = Field(default=None)
    baseline_features: Optional[FeatureDict] = Field(default=None)


class Patient(BaseModel):
    patient_id: str
    name: str
    status: Literal["stable", "attention", "alert"]
    last_check_in: datetime
    speech_trend: str
    cognitive_trend: str
    alerts: int = Field(ge=0)


class AssessmentHistoryItem(BaseModel):
    patient_id: str
    test_id: str
    timestamp: datetime
    status: Literal["stable", "attention"]
    deviation_score: float = Field(ge=0, le=1)
    speech_rate: int = Field(ge=0)
    pause_score: float = Field(ge=0, le=1)
    message: str


class SOSCreateRequest(BaseModel):
    message: Optional[str] = None


class SOSAlertResponse(BaseModel):
    id: int
    patient_id: str
    patient_name: str = "Unknown Patient"
    timestamp: datetime
    status: Literal["active", "resolved"]
    message: str
    resolved_at: Optional[datetime] = None
class CognitiveTestRequest(BaseModel):
    patient_id: str = Field(min_length=1, examples=["NW-1024"])
    test_id: str = Field(min_length=1, examples=["cog-2026-08-31-001"])
    timestamp: datetime
    orientation_score: float
    memory_score: float
    attention_score: float
    reasoning_score: float
    overall_score: float

class CognitiveTestResponse(BaseModel):
    id: int
    patient_id: str
    test_id: str
    timestamp: datetime
    orientation_score: float
    memory_score: float
    attention_score: float
    reasoning_score: float
    overall_score: float
    status: Literal["stable", "attention", "significant_change", "baseline_establishing"]
    message: str
