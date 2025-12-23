"""
Pose Detector - Abstract base class for pose detection.

Defines the interface for all pose detection implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class PoseType(Enum):
    """Detected pose type classification."""

    UNKNOWN = "unknown"
    STANDING = "standing"
    SITTING = "sitting"
    SQUATTING = "squatting"
    BENDING = "bending"
    BRACE_POSITION = "brace_position"


class BodyPart(Enum):
    """Body part identifiers for MediaPipe 33-point model."""

    # Face
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10

    # Upper body
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22

    # Lower body
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


@dataclass
class Landmark:
    """A single body landmark with 3D coordinates and visibility."""

    x: float  # Normalized x coordinate (0-1)
    y: float  # Normalized y coordinate (0-1)
    z: float  # Depth relative to hip center
    visibility: float  # Confidence score (0-1)

    def to_pixel(self, width: int, height: int) -> Tuple[int, int]:
        """Convert normalized coordinates to pixel coordinates."""
        return int(self.x * width), int(self.y * height)

    def to_array(self) -> np.ndarray:
        """Convert to numpy array [x, y, z]."""
        return np.array([self.x, self.y, self.z])


@dataclass
class JointAngles:
    """Calculated joint angles in degrees."""

    # Upper body
    left_elbow: Optional[float] = None
    right_elbow: Optional[float] = None
    left_shoulder: Optional[float] = None
    right_shoulder: Optional[float] = None

    # Spine
    neck: Optional[float] = None  # Head-neck angle
    torso: Optional[float] = None  # Upper body lean angle

    # Lower body
    left_knee: Optional[float] = None
    right_knee: Optional[float] = None
    left_hip: Optional[float] = None
    right_hip: Optional[float] = None

    def to_dict(self) -> Dict[str, Optional[float]]:
        """Convert to dictionary."""
        return {
            "left_elbow": self.left_elbow,
            "right_elbow": self.right_elbow,
            "left_shoulder": self.left_shoulder,
            "right_shoulder": self.right_shoulder,
            "neck": self.neck,
            "torso": self.torso,
            "left_knee": self.left_knee,
            "right_knee": self.right_knee,
            "left_hip": self.left_hip,
            "right_hip": self.right_hip,
        }


@dataclass
class PoseResult:
    """Result of pose detection on a single frame."""

    # Detection status
    detected: bool  # Whether a pose was detected
    confidence: float  # Overall detection confidence (0-1)

    # Landmarks (33 points for MediaPipe)
    landmarks: List[Landmark] = field(default_factory=list)

    # Calculated values
    angles: Optional[JointAngles] = None
    pose_type: PoseType = PoseType.UNKNOWN

    # Metadata
    timestamp: float = 0.0
    frame_number: int = 0

    def get_landmark(self, part: BodyPart) -> Optional[Landmark]:
        """Get landmark by body part enum."""
        if part.value < len(self.landmarks):
            return self.landmarks[part.value]
        return None

    def get_landmarks_array(self) -> np.ndarray:
        """Get all landmarks as numpy array (33, 3)."""
        if not self.landmarks:
            return np.array([])
        return np.array([[lm.x, lm.y, lm.z] for lm in self.landmarks])

    def get_visibility_array(self) -> np.ndarray:
        """Get visibility scores as numpy array (33,)."""
        if not self.landmarks:
            return np.array([])
        return np.array([lm.visibility for lm in self.landmarks])


class PoseDetector(ABC):
    """
    Abstract base class for pose detectors.

    All pose detection implementations must inherit from this class.

    Usage:
        detector = MediaPipePose()
        result = detector.detect(frame)
        if result.detected:
            for landmark in result.landmarks:
                print(f"x={landmark.x}, y={landmark.y}")
    """

    def __init__(self) -> None:
        self._is_initialized: bool = False
        self._frame_count: int = 0

    @abstractmethod
    def detect(self, frame: np.ndarray) -> PoseResult:
        """
        Detect pose in a single frame.

        Args:
            frame: BGR image as numpy array (H, W, 3)

        Returns:
            PoseResult containing landmarks and metadata
        """
        pass

    @abstractmethod
    def release(self) -> None:
        """Release detector resources."""
        pass

    @property
    def is_initialized(self) -> bool:
        """Check if detector is initialized."""
        return self._is_initialized

    def __enter__(self) -> "PoseDetector":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Context manager exit - release resources."""
        self.release()


# Skeleton connection definitions for visualization
POSE_CONNECTIONS: List[Tuple[BodyPart, BodyPart]] = [
    # Face
    (BodyPart.NOSE, BodyPart.LEFT_EYE_INNER),
    (BodyPart.LEFT_EYE_INNER, BodyPart.LEFT_EYE),
    (BodyPart.LEFT_EYE, BodyPart.LEFT_EYE_OUTER),
    (BodyPart.LEFT_EYE_OUTER, BodyPart.LEFT_EAR),
    (BodyPart.NOSE, BodyPart.RIGHT_EYE_INNER),
    (BodyPart.RIGHT_EYE_INNER, BodyPart.RIGHT_EYE),
    (BodyPart.RIGHT_EYE, BodyPart.RIGHT_EYE_OUTER),
    (BodyPart.RIGHT_EYE_OUTER, BodyPart.RIGHT_EAR),
    (BodyPart.MOUTH_LEFT, BodyPart.MOUTH_RIGHT),
    # Upper body
    (BodyPart.LEFT_SHOULDER, BodyPart.RIGHT_SHOULDER),
    (BodyPart.LEFT_SHOULDER, BodyPart.LEFT_ELBOW),
    (BodyPart.LEFT_ELBOW, BodyPart.LEFT_WRIST),
    (BodyPart.LEFT_WRIST, BodyPart.LEFT_PINKY),
    (BodyPart.LEFT_WRIST, BodyPart.LEFT_INDEX),
    (BodyPart.LEFT_WRIST, BodyPart.LEFT_THUMB),
    (BodyPart.LEFT_PINKY, BodyPart.LEFT_INDEX),
    (BodyPart.RIGHT_SHOULDER, BodyPart.RIGHT_ELBOW),
    (BodyPart.RIGHT_ELBOW, BodyPart.RIGHT_WRIST),
    (BodyPart.RIGHT_WRIST, BodyPart.RIGHT_PINKY),
    (BodyPart.RIGHT_WRIST, BodyPart.RIGHT_INDEX),
    (BodyPart.RIGHT_WRIST, BodyPart.RIGHT_THUMB),
    (BodyPart.RIGHT_PINKY, BodyPart.RIGHT_INDEX),
    # Torso
    (BodyPart.LEFT_SHOULDER, BodyPart.LEFT_HIP),
    (BodyPart.RIGHT_SHOULDER, BodyPart.RIGHT_HIP),
    (BodyPart.LEFT_HIP, BodyPart.RIGHT_HIP),
    # Lower body
    (BodyPart.LEFT_HIP, BodyPart.LEFT_KNEE),
    (BodyPart.LEFT_KNEE, BodyPart.LEFT_ANKLE),
    (BodyPart.LEFT_ANKLE, BodyPart.LEFT_HEEL),
    (BodyPart.LEFT_ANKLE, BodyPart.LEFT_FOOT_INDEX),
    (BodyPart.LEFT_HEEL, BodyPart.LEFT_FOOT_INDEX),
    (BodyPart.RIGHT_HIP, BodyPart.RIGHT_KNEE),
    (BodyPart.RIGHT_KNEE, BodyPart.RIGHT_ANKLE),
    (BodyPart.RIGHT_ANKLE, BodyPart.RIGHT_HEEL),
    (BodyPart.RIGHT_ANKLE, BodyPart.RIGHT_FOOT_INDEX),
    (BodyPart.RIGHT_HEEL, BodyPart.RIGHT_FOOT_INDEX),
]
