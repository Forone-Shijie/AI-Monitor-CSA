"""
Perception Module - Pose Detection and Speech Recognition.

This module provides pose detection and ASR capabilities:

Pose Detection (COCO 17-point format):
    - PoseDetector: Abstract base class for pose detectors
    - RTMPoseDetector: GPU-accelerated multi-person pose detection (MMPose)
    - MultiPersonPoseResult: Result container for multi-person detection
    - PoseResult: Result container for single-person pose detection
    - Landmark: Single body landmark with coordinates
    - JointAngles: Calculated joint angles

Speech Recognition:
    - ASREngine: Abstract base class for ASR engines
    - DoubaoASREngine: Volcengine Doubao streaming ASR (bigmodel_async)
    - DoubaoStreamingSession: Session manager for streaming recognition
    - ASRResult: Result container for transcription
    - ASRSegment: Single transcribed segment

Usage:
    from src.perception import RTMPoseDetector, PoseResult

    # Single person detection
    with RTMPoseDetector(device='cuda:0') as detector:
        result = detector.detect(frame)
        if result.detected:
            for landmark in result.landmarks:
                print(f"({landmark.x:.3f}, {landmark.y:.3f})")

    # Multi-person detection
    with RTMPoseDetector() as detector:
        multi_result = detector.detect_multi(frame)
        for pose in multi_result.poses:
            print(f"Person confidence: {pose.confidence}")

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
from .pose_detector import (
    BodyPart,
    JointAngles,
    Landmark,
    NUM_KEYPOINTS,
    POSE_CONNECTIONS,
    PoseDetector,
    PoseResult,
    PoseType,
)
from .rtmpose_detector import (
    MultiPersonPoseResult,
    RTMPoseDetector,
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
    "NUM_KEYPOINTS",
    # Pose Detection - RTMPose Implementation
    "RTMPoseDetector",
    "MultiPersonPoseResult",
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
