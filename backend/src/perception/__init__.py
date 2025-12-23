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
    - WhisperASR: OpenAI Whisper-based local ASR (offline)
    - DoubaoASR: Volcengine Doubao API (online)
    - HybridASR: Smart switcher with auto fallback
    - ASRResult: Result container for transcription
    - ASRSegment: Single transcribed segment

Usage:
    from src.perception import MediaPipePose, PoseResult

    with MediaPipePose() as detector:
        result = detector.detect(frame)
        if result.detected:
            for landmark in result.landmarks:
                print(f"({landmark.x:.3f}, {landmark.y:.3f})")

    # Smart ASR with auto fallback (online -> offline)
    from src.perception import HybridASR

    with HybridASR() as asr:
        result = asr.transcribe(audio_data)
        print(f"Mode: {asr.current_mode}")
        print(f"Text: {result.text}")
"""

from .asr_engine import (
    ASREngine,
    ASRLanguage,
    ASRResult,
    ASRSegment,
    ASRStatus,
    STANDARD_TERMINOLOGY,
)
from .doubao_asr import DoubaoASR, DoubaoConfig, MockDoubaoASR
from .hybrid_asr import ASRMode, HybridASR, MockHybridASR
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
from .whisper_asr import MockWhisperASR, WhisperASR

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
    # ASR - Whisper (offline)
    "WhisperASR",
    "MockWhisperASR",
    # ASR - Doubao (online)
    "DoubaoASR",
    "DoubaoConfig",
    "MockDoubaoASR",
    # ASR - Hybrid (auto switch)
    "HybridASR",
    "MockHybridASR",
    "ASRMode",
]
