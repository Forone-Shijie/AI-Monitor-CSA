"""
MediaPipe Pose - Pose detection using Google MediaPipe.

Provides real-time pose estimation with 33 body landmarks.
"""

import time
from typing import Optional

import cv2
import numpy as np

from .pose_detector import (
    JointAngles,
    Landmark,
    PoseDetector,
    PoseResult,
    PoseType,
)


class MediaPipePose(PoseDetector):
    """
    Pose detector using Google MediaPipe Pose.

    MediaPipe Pose provides 33 body landmarks in real-time.

    Usage:
        with MediaPipePose() as detector:
            result = detector.detect(frame)
            if result.detected:
                print(f"Confidence: {result.confidence}")
                for lm in result.landmarks:
                    print(f"  ({lm.x:.3f}, {lm.y:.3f})")

    Attributes:
        model_complexity: Model complexity (0, 1, or 2)
        min_detection_confidence: Minimum detection confidence (0-1)
        min_tracking_confidence: Minimum tracking confidence (0-1)
    """

    def __init__(
        self,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        static_image_mode: bool = False,
        enable_segmentation: bool = False,
    ) -> None:
        """
        Initialize MediaPipe Pose detector.

        Args:
            model_complexity: Model complexity (0=lite, 1=full, 2=heavy)
            min_detection_confidence: Minimum confidence for detection
            min_tracking_confidence: Minimum confidence for tracking
            static_image_mode: If True, treats each image independently
            enable_segmentation: Enable segmentation mask output
        """
        super().__init__()

        self._model_complexity = model_complexity
        self._min_detection_confidence = min_detection_confidence
        self._min_tracking_confidence = min_tracking_confidence
        self._static_image_mode = static_image_mode
        self._enable_segmentation = enable_segmentation

        self._pose = None
        self._mp_pose = None
        self._mp_drawing = None

        self._initialize()

    def _initialize(self) -> None:
        """Initialize MediaPipe Pose model."""
        try:
            import mediapipe as mp

            self._mp_pose = mp.solutions.pose
            self._mp_drawing = mp.solutions.drawing_utils

            self._pose = self._mp_pose.Pose(
                static_image_mode=self._static_image_mode,
                model_complexity=self._model_complexity,
                enable_segmentation=self._enable_segmentation,
                min_detection_confidence=self._min_detection_confidence,
                min_tracking_confidence=self._min_tracking_confidence,
            )

            self._is_initialized = True

        except ImportError:
            raise ImportError(
                "mediapipe is required for pose detection. "
                "Install with: pip install mediapipe"
            )

    def detect(self, frame: np.ndarray) -> PoseResult:
        """
        Detect pose in a single frame.

        Args:
            frame: BGR image as numpy array (H, W, 3)

        Returns:
            PoseResult containing landmarks and metadata
        """
        if not self._is_initialized or self._pose is None:
            return PoseResult(detected=False, confidence=0.0)

        timestamp = time.time()
        self._frame_count += 1

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the frame
        results = self._pose.process(rgb_frame)

        # Check if pose was detected
        if results.pose_landmarks is None:
            return PoseResult(
                detected=False,
                confidence=0.0,
                timestamp=timestamp,
                frame_number=self._frame_count,
            )

        # Extract landmarks
        landmarks = []
        total_visibility = 0.0

        for lm in results.pose_landmarks.landmark:
            landmark = Landmark(
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibility=lm.visibility,
            )
            landmarks.append(landmark)
            total_visibility += lm.visibility

        # Calculate average confidence
        avg_confidence = total_visibility / len(landmarks) if landmarks else 0.0

        # Calculate joint angles
        angles = self._calculate_angles(landmarks)

        # Classify pose type
        pose_type = self._classify_pose(landmarks, angles)

        return PoseResult(
            detected=True,
            confidence=avg_confidence,
            landmarks=landmarks,
            angles=angles,
            pose_type=pose_type,
            timestamp=timestamp,
            frame_number=self._frame_count,
        )

    def _calculate_angles(self, landmarks: list[Landmark]) -> JointAngles:
        """
        Calculate joint angles from landmarks.

        Uses vector math to calculate angles between body segments.
        """
        if len(landmarks) < 33:
            return JointAngles()

        def get_angle(p1: Landmark, p2: Landmark, p3: Landmark) -> float:
            """Calculate angle at p2 formed by p1-p2-p3."""
            v1 = np.array([p1.x - p2.x, p1.y - p2.y])
            v2 = np.array([p3.x - p2.x, p3.y - p2.y])

            # Handle zero vectors
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0

            cos_angle = np.dot(v1, v2) / (norm1 * norm2)
            # Clamp to valid range for arccos
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle = np.degrees(np.arccos(cos_angle))
            return float(angle)

        # Get landmarks by index (MediaPipe standard)
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_elbow = landmarks[13]
        right_elbow = landmarks[14]
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        left_hip = landmarks[23]
        right_hip = landmarks[24]
        left_knee = landmarks[25]
        right_knee = landmarks[26]
        left_ankle = landmarks[27]
        right_ankle = landmarks[28]
        nose = landmarks[0]

        # Calculate angles
        angles = JointAngles()

        # Elbow angles (shoulder-elbow-wrist)
        angles.left_elbow = get_angle(left_shoulder, left_elbow, left_wrist)
        angles.right_elbow = get_angle(right_shoulder, right_elbow, right_wrist)

        # Shoulder angles (elbow-shoulder-hip)
        angles.left_shoulder = get_angle(left_elbow, left_shoulder, left_hip)
        angles.right_shoulder = get_angle(right_elbow, right_shoulder, right_hip)

        # Knee angles (hip-knee-ankle)
        angles.left_knee = get_angle(left_hip, left_knee, left_ankle)
        angles.right_knee = get_angle(right_hip, right_knee, right_ankle)

        # Hip angles (shoulder-hip-knee)
        angles.left_hip = get_angle(left_shoulder, left_hip, left_knee)
        angles.right_hip = get_angle(right_shoulder, right_hip, right_knee)

        # Torso angle (lean from vertical)
        mid_shoulder = Landmark(
            x=(left_shoulder.x + right_shoulder.x) / 2,
            y=(left_shoulder.y + right_shoulder.y) / 2,
            z=(left_shoulder.z + right_shoulder.z) / 2,
            visibility=(left_shoulder.visibility + right_shoulder.visibility) / 2,
        )
        mid_hip = Landmark(
            x=(left_hip.x + right_hip.x) / 2,
            y=(left_hip.y + right_hip.y) / 2,
            z=(left_hip.z + right_hip.z) / 2,
            visibility=(left_hip.visibility + right_hip.visibility) / 2,
        )

        # Calculate torso angle from vertical
        dx = mid_shoulder.x - mid_hip.x
        dy = mid_shoulder.y - mid_hip.y
        # Note: In image coordinates, y increases downward
        torso_angle = np.degrees(np.arctan2(dx, -dy))
        angles.torso = float(abs(torso_angle))

        # Neck angle (mid_shoulder to nose vs vertical)
        dx_neck = nose.x - mid_shoulder.x
        dy_neck = nose.y - mid_shoulder.y
        neck_angle = np.degrees(np.arctan2(dx_neck, -dy_neck))
        angles.neck = float(abs(neck_angle))

        return angles

    def _classify_pose(
        self, landmarks: list[Landmark], angles: JointAngles
    ) -> PoseType:
        """
        Classify the detected pose into a type.

        Simple rule-based classification based on joint angles.
        """
        if not angles or len(landmarks) < 33:
            return PoseType.UNKNOWN

        # Get key angles
        left_knee = angles.left_knee or 180
        right_knee = angles.right_knee or 180
        avg_knee = (left_knee + right_knee) / 2

        left_hip = angles.left_hip or 180
        right_hip = angles.right_hip or 180
        avg_hip = (left_hip + right_hip) / 2

        torso = angles.torso or 0

        # Classification rules
        # Brace position: knees ~90°, torso forward, arms specific position
        if 70 <= avg_knee <= 110 and torso > 20:
            # Additional check for brace position
            left_elbow = angles.left_elbow or 180
            right_elbow = angles.right_elbow or 180
            avg_elbow = (left_elbow + right_elbow) / 2
            if avg_elbow < 120:  # Arms bent
                return PoseType.BRACE_POSITION

        # Squatting: knees bent significantly
        if avg_knee < 100 and avg_hip < 100:
            return PoseType.SQUATTING

        # Bending: torso leaning forward significantly
        if torso > 30 and avg_knee > 150:
            return PoseType.BENDING

        # Sitting: knees bent, relatively upright torso
        if avg_knee < 120 and torso < 20:
            return PoseType.SITTING

        # Standing: relatively straight knees and torso
        if avg_knee > 150 and torso < 15:
            return PoseType.STANDING

        return PoseType.UNKNOWN

    def get_drawing_spec(self) -> tuple:
        """
        Get MediaPipe drawing specifications.

        Returns:
            Tuple of (landmark_style, connection_style)
        """
        if self._mp_drawing is None:
            return None, None

        landmark_style = self._mp_drawing.DrawingSpec(
            color=(0, 255, 0),  # Green
            thickness=2,
            circle_radius=3,
        )
        connection_style = self._mp_drawing.DrawingSpec(
            color=(0, 212, 255),  # Cyan (HUD style)
            thickness=2,
        )
        return landmark_style, connection_style

    def draw_landmarks(
        self,
        frame: np.ndarray,
        result: PoseResult,
        draw_connections: bool = True,
    ) -> np.ndarray:
        """
        Draw pose landmarks on frame.

        Args:
            frame: BGR image to draw on
            result: PoseResult from detect()
            draw_connections: Whether to draw skeleton connections

        Returns:
            Frame with landmarks drawn
        """
        if not result.detected or not result.landmarks:
            return frame

        output = frame.copy()
        h, w = output.shape[:2]

        # Draw connections first (so landmarks are on top)
        if draw_connections:
            from .pose_detector import POSE_CONNECTIONS

            for start_part, end_part in POSE_CONNECTIONS:
                start_lm = result.get_landmark(start_part)
                end_lm = result.get_landmark(end_part)

                if start_lm and end_lm:
                    # Only draw if both landmarks are visible enough
                    if start_lm.visibility > 0.5 and end_lm.visibility > 0.5:
                        start_pt = start_lm.to_pixel(w, h)
                        end_pt = end_lm.to_pixel(w, h)
                        cv2.line(output, start_pt, end_pt, (0, 212, 255), 2)

        # Draw landmarks
        for lm in result.landmarks:
            if lm.visibility > 0.5:
                pt = lm.to_pixel(w, h)
                cv2.circle(output, pt, 4, (0, 255, 0), -1)
                cv2.circle(output, pt, 6, (0, 212, 255), 1)

        return output

    def release(self) -> None:
        """Release MediaPipe resources."""
        if self._pose is not None:
            self._pose.close()
            self._pose = None
        self._is_initialized = False

    @property
    def model_complexity(self) -> int:
        """Get model complexity level."""
        return self._model_complexity
