"""
API Schemas - Pydantic models for request/response validation.

Defines data models for:
- Session management
- Monitoring data
- Evaluation results
- Configuration
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class SessionStatus(str, Enum):
    """Training session status."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ScenarioType(str, Enum):
    """Supported scenario types."""

    BRACE_POSITION = "brace_position"
    FIRE_EMERGENCY = "fire_emergency"
    EVACUATION = "evacuation"
    MEDICAL_EMERGENCY = "medical_emergency"


class VideoSourceType(str, Enum):
    """Video source types."""

    CAMERA = "camera"
    FILE = "file"
    RTSP = "rtsp"


# =============================================================================
# Base Models
# =============================================================================


class BaseResponse(BaseModel):
    """Base response model."""

    success: bool = True
    message: str = "OK"
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Session Schemas
# =============================================================================


class SessionCreate(BaseModel):
    """Request to create a new session."""

    trainee_id: str = Field(..., description="Trainee identifier")
    trainee_name: str = Field(..., description="Trainee name")
    scenario_id: str = Field(default="brace_position", description="Scenario ID")
    video_source: VideoSourceType = Field(
        default=VideoSourceType.CAMERA, description="Video source type"
    )
    video_path: Optional[str] = Field(
        None, description="Video file path or RTSP URL"
    )
    camera_id: int = Field(default=0, description="Camera device ID")
    audio_device_id: Optional[int] = Field(
        default=None, description="Audio device ID for ASR"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trainee_id": "T001",
                "trainee_name": "张三",
                "scenario_id": "brace_position",
                "video_source": "camera",
                "camera_id": 0,
                "audio_device_id": None,
            }
        }


class SessionInfo(BaseModel):
    """Session information."""

    session_id: str
    trainee_id: str
    trainee_name: str
    scenario_id: str
    scenario_name: str
    status: SessionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_20231223_001",
                "trainee_id": "T001",
                "trainee_name": "张三",
                "scenario_id": "brace_position",
                "scenario_name": "防冲击姿势",
                "status": "created",
                "created_at": "2023-12-23T10:00:00",
                "duration_seconds": 0.0,
            }
        }


class SessionResponse(BaseResponse):
    """Response with session data."""

    data: SessionInfo


class SessionListResponse(BaseResponse):
    """Response with session list."""

    data: List[SessionInfo]
    total: int = 0


class SessionStartRequest(BaseModel):
    """Request to start monitoring."""

    trigger_type: str = Field(default="manual", description="Trigger type")


class SessionStopRequest(BaseModel):
    """Request to stop monitoring."""

    generate_report: bool = Field(
        default=True, description="Whether to generate report"
    )


class SessionUpdate(BaseModel):
    """Request to update session parameters (only allowed in non-running states)."""

    trainee_id: Optional[str] = Field(None, description="Trainee identifier")
    trainee_name: Optional[str] = Field(None, description="Trainee name")
    scenario_id: Optional[str] = Field(None, description="Scenario ID")
    camera_id: Optional[int] = Field(None, description="Camera device ID")
    audio_device_id: Optional[int] = Field(None, description="Audio device ID for ASR")

    class Config:
        json_schema_extra = {
            "example": {
                "trainee_id": "T002",
                "trainee_name": "李四",
                "scenario_id": "fire_emergency",
                "camera_id": 1,
                "audio_device_id": 0,
            }
        }


# =============================================================================
# Monitoring Schemas
# =============================================================================


class PoseData(BaseModel):
    """Pose detection data."""

    timestamp: float
    detected: bool = False
    keypoints: Optional[List[List[float]]] = None
    angles: Optional[Dict[str, float]] = None
    pose_type: Optional[str] = None
    confidence: float = 0.0


class ActionData(BaseModel):
    """Action recognition data."""

    timestamp: float
    action_id: str
    action_name: str
    confidence: float = 0.0
    duration: float = 0.0


class ASRData(BaseModel):
    """Speech recognition data."""

    timestamp: float
    text: str
    confidence: float = 0.0
    is_final: bool = False


class BracePositionData(BaseModel):
    """Brace position detection data."""

    timestamp: float
    is_compliant: bool = False
    body_lean_angle: float = 0.0
    head_position: str = ""
    arm_position: str = ""
    overall_score: float = 0.0
    feedback: List[str] = []


class MonitoringFrame(BaseModel):
    """Real-time monitoring frame data."""

    session_id: str
    frame_number: int
    timestamp: float
    pose: Optional[PoseData] = None
    action: Optional[ActionData] = None
    asr: Optional[ASRData] = None
    brace: Optional[BracePositionData] = None
    events: List[str] = []


class MonitoringStatus(BaseModel):
    """Monitoring status."""

    session_id: str
    is_running: bool = False
    frame_count: int = 0
    elapsed_seconds: float = 0.0
    fps: float = 0.0
    last_update: Optional[datetime] = None


# =============================================================================
# Evaluation Schemas
# =============================================================================


class DimensionScoreData(BaseModel):
    """Score for a single dimension."""

    dimension: str
    score: float
    weight: float
    weighted_score: float
    grade: str
    feedback: List[str] = []


class EvaluationData(BaseModel):
    """Evaluation result data."""

    session_id: str
    scenario_id: str
    scenario_name: str
    total_score: float
    grade: str
    pose_score: float = 0.0
    action_score: float = 0.0
    communication_score: float = 0.0
    dimension_scores: Dict[str, DimensionScoreData] = {}
    strengths: List[str] = []
    improvements: List[str] = []
    summary: str = ""


class EvaluationResponse(BaseResponse):
    """Response with evaluation data."""

    data: EvaluationData


# =============================================================================
# Report Schemas
# =============================================================================


class SuggestionData(BaseModel):
    """Improvement suggestion."""

    category: str
    priority: int
    issue: str
    suggestion: str
    example: Optional[str] = None


class ReportData(BaseModel):
    """Training report data."""

    report_id: str
    generated_at: datetime
    session_id: str
    trainee_id: str
    trainee_name: str
    scenario_id: str
    scenario_name: str
    session_date: str
    duration_seconds: float
    total_score: float
    grade: str
    pose_score: float
    action_score: float
    communication_score: float
    suggestions: List[SuggestionData] = []
    ai_summary: str = ""
    strengths: List[str] = []
    improvements: List[str] = []


class ReportResponse(BaseResponse):
    """Response with report data."""

    data: ReportData


class ReportListResponse(BaseResponse):
    """Response with report list."""

    data: List[ReportData]
    total: int = 0


# =============================================================================
# Playback Schemas
# =============================================================================


class PlaybackFrame(BaseModel):
    """Playback frame data."""

    frame_number: int
    timestamp: float
    pose: Optional[PoseData] = None
    action: Optional[ActionData] = None
    asr: Optional[ASRData] = None
    brace: Optional[BracePositionData] = None


class PlaybackData(BaseModel):
    """Playback data for a session."""

    session_id: str
    total_frames: int
    duration_seconds: float
    fps: float
    frames: List[PlaybackFrame] = []


class PlaybackResponse(BaseResponse):
    """Response with playback data."""

    data: PlaybackData


# =============================================================================
# Configuration Schemas
# =============================================================================


class SOPRuleData(BaseModel):
    """SOP rule configuration."""

    scenario_id: str
    name: str
    trigger_keywords: List[str] = []
    trigger_event: Optional[str] = None
    max_total_time: float = 60.0
    steps: List[Dict[str, Any]] = []


class EvaluationWeightsData(BaseModel):
    """Evaluation weights configuration."""

    pose: float = 0.30
    action: float = 0.40
    communication: float = 0.30


class ConfigData(BaseModel):
    """System configuration."""

    sop_rules: Dict[str, SOPRuleData] = {}
    evaluation_weights: EvaluationWeightsData = EvaluationWeightsData()
    video_fps: int = 30
    pose_detection_confidence: float = 0.5
    asr_mode: str = "auto"


class ConfigResponse(BaseResponse):
    """Response with configuration."""

    data: ConfigData


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration."""

    evaluation_weights: Optional[EvaluationWeightsData] = None
    video_fps: Optional[int] = None
    pose_detection_confidence: Optional[float] = None
    asr_mode: Optional[str] = None


# =============================================================================
# WebSocket Schemas
# =============================================================================


class WSMessage(BaseModel):
    """WebSocket message."""

    type: str  # frame, status, error, event
    data: Dict[str, Any]
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())


class WSSubscribeRequest(BaseModel):
    """WebSocket subscribe request."""

    session_id: str
    data_types: List[str] = ["pose", "action", "asr", "brace"]
