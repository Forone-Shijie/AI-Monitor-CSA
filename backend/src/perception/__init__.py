"""
Perception Module - Pose Detection and Speech Recognition.

This module provides pose detection and ASR capabilities:

Pose Detection:
    - PoseDetector: Abstract base class for pose detectors
    - MediaPipePose: MediaPipe-based pose detection
    - PoseResult: Result container for pose detection
    - Landmark: Single body landmark with coordinates
    - JointAngles: Calculated joint angles

Speech Recognition:
    - ASREngine: Abstract base class for ASR engines
    - DoubaoASREngine: Volcengine Doubao streaming ASR (bigmodel_async)
    - DoubaoStreamingSession: Session manager for streaming recognition
    - ASRResult: Result container for transcription
    - ASRSegment: Single transcribed segment

Usage:
    from src.perception import MediaPipePose, PoseResult

    with MediaPipePose() as detector:
        result = detector.detect(frame)
        if result.detected:
            for landmark in result.landmarks:
                print(f"({landmark.x:.3f}, {landmark.y:.3f})")

    # Streaming ASR
    from src.perception import DoubaoStreamingSession

    session = DoubaoStreamingSession()
    await session.start()
    await session.send_audio(audio_data)
    text = session.get_current_text()
"""

from .asr_engine import (
    ASREngine,
    ASRLanguage,
    ASRResult,
    ASRSegment,
    ASRStatus,
    STANDARD_TERMINOLOGY,
)
from .doubao_asr_engine import (
    DoubaoASREngine,
    DoubaoConfig,
    DoubaoResponse,
    DoubaoStreamingSession,
)
from .mediapipe_pose import MediaPipePose
from .pose_detector import (
    BodyPart,
    JointAngles,
    Landmark,
    POSE_CONNECTIONS,
    PoseDetector,
    PoseResult,
    PoseType,
)

__all__ = [
    # Pose Detection - Base classes
    "PoseDetector",
    "PoseResult",
    "Landmark",
    "JointAngles",
    "PoseType",
    "BodyPart",
    "POSE_CONNECTIONS",
    # Pose Detection - Implementations
    "MediaPipePose",
    # ASR - Base classes
    "ASREngine",
    "ASRResult",
    "ASRSegment",
    "ASRLanguage",
    "ASRStatus",
    "STANDARD_TERMINOLOGY",
    # ASR - Doubao Streaming (bigmodel_async)
    "DoubaoASREngine",
    "DoubaoConfig",
    "DoubaoResponse",
    "DoubaoStreamingSession",
]
