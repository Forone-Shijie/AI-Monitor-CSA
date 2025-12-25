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
    - ASRResult: Result container for transcription
    - ASRSegment: Single transcribed segment

Note:
    后续将添加 FunASR Paraformer 支持本地高精度流式识别。

Usage:
    from src.perception import MediaPipePose, PoseResult

    with MediaPipePose() as detector:
        result = detector.detect(frame)
        if result.detected:
            for landmark in result.landmarks:
                print(f"({landmark.x:.3f}, {landmark.y:.3f})")

    # ASR usage (FunASR implementation planned)
    # from src.perception import FunASREngine
    # with FunASREngine() as asr:
    #     result = asr.transcribe(audio_data)
    #     print(f"Text: {result.text}")
"""

from .asr_engine import (
    ASREngine,
    ASRLanguage,
    ASRResult,
    ASRSegment,
    ASRStatus,
    STANDARD_TERMINOLOGY,
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
]
