"""
RTMPose Detector - Multi-person pose detection using MMPose RTMPose.

Provides GPU-accelerated multi-person pose estimation with COCO 17 keypoints.
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np

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

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class MultiPersonPoseResult:
    """Result container for multi-person pose detection."""

    poses: List[PoseResult]
    timestamp: float = 0.0
    frame_number: int = 0

    @property
    def num_persons(self) -> int:
        """Get number of detected persons."""
        return len(self.poses)

    def get_primary_pose(self) -> Optional[PoseResult]:
        """Get the primary (most confident) pose."""
        if not self.poses:
            return None
        return max(self.poses, key=lambda p: p.confidence)


class RTMPoseDetector(PoseDetector):
    """
    Multi-person pose detector using MMPose RTMPose.

    Provides GPU-accelerated inference with COCO 17 keypoints format.
    Supports detecting multiple persons simultaneously.

    Features:
    - GPU-accelerated inference (CUDA)
    - Multi-person detection (configurable max persons)
    - Automatic model download on first run
    - 30+ FPS on RTX 3090 / RTX 4070 Laptop

    Usage:
        # Single person detection (returns most confident)
        with RTMPoseDetector(device='cuda:0') as detector:
            result = detector.detect(frame)
            if result.detected:
                print(f"Confidence: {result.confidence}")

        # Multi-person detection
        with RTMPoseDetector() as detector:
            multi_result = detector.detect_multi(frame)
            for pose in multi_result.poses:
                print(f"Person confidence: {pose.confidence}")

    Attributes:
        device: Device for inference ('cuda:0', 'cuda:1', 'cpu')
        det_score_thr: Detection confidence threshold
        pose_score_thr: Pose keypoint confidence threshold
        max_persons: Maximum number of persons to detect
    """

    def __init__(
        self,
        device: str = "cuda:0",
        det_score_thr: float = 0.3,
        pose_score_thr: float = 0.3,
        max_persons: int = 5,
    ) -> None:
        """
        Initialize RTMPose detector.

        Args:
            device: Device to run inference ('cuda:0', 'cuda:1', 'cpu')
            det_score_thr: Detection confidence threshold (0-1)
            pose_score_thr: Pose keypoint confidence threshold (0-1)
            max_persons: Maximum number of persons to detect
        """
        super().__init__()

        self._device = device
        self._det_score_thr = det_score_thr
        self._pose_score_thr = pose_score_thr
        self._max_persons = max_persons

        self._inferencer = None

        self._initialize()

    def _initialize(self) -> None:
        """Initialize MMPose models with automatic download."""
        try:
            import torch
            from mmpose.apis import MMPoseInferencer

            # Check CUDA availability
            if "cuda" in self._device and not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                self._device = "cpu"

            logger.info(f"Initializing RTMPose on {self._device}...")

            # Use MMPoseInferencer - high-level API that handles everything
            # Full model names from mmpose model-index.yml
            # Models are auto-downloaded on first use
            self._inferencer = MMPoseInferencer(
                pose2d='rtmpose-m_8xb256-420e_coco-256x192',  # RTMPose-M COCO
                pose2d_weights=None,  # Auto-download
                device=self._device,
            )

            self._is_initialized = True
            logger.info(f"RTMPose initialized successfully on {self._device}")

        except ImportError as e:
            raise ImportError(
                f"MMPose not installed properly: {e}. "
                "Install with:\n"
                "  pip install openmim\n"
                "  mim install mmengine mmcv mmdet mmpose"
            )
        except Exception as e:
            logger.error(f"RTMPose initialization failed: {e}")
            self._is_initialized = False
            raise

    def detect(self, frame: np.ndarray) -> PoseResult:
        """
        Detect pose in a single frame (returns primary person).

        For backward compatibility, returns only the most confident pose.

        Args:
            frame: BGR image as numpy array (H, W, 3)

        Returns:
            PoseResult containing landmarks and metadata
        """
        multi_result = self.detect_multi(frame)
        primary = multi_result.get_primary_pose()

        if primary is None:
            return PoseResult(
                detected=False,
                confidence=0.0,
                timestamp=multi_result.timestamp,
                frame_number=multi_result.frame_number,
            )

        return primary

    def detect_multi(self, frame: np.ndarray) -> MultiPersonPoseResult:
        """
        Detect poses for multiple persons in a frame.

        Args:
            frame: BGR image as numpy array (H, W, 3)

        Returns:
            MultiPersonPoseResult with all detected poses
        """
        timestamp = time.time()
        self._frame_count += 1

        if not self._is_initialized:
            return MultiPersonPoseResult([], timestamp, self._frame_count)

        try:
            # Use MMPoseInferencer for inference
            # Returns a generator, we take the first result
            results = next(self._inferencer(
                frame,
                return_vis=False,
                det_bbox_thr=self._det_score_thr,
                kpt_thr=self._pose_score_thr,
            ))

            predictions = results.get('predictions', [[]])
            if not predictions or not predictions[0]:
                return MultiPersonPoseResult([], timestamp, self._frame_count)

            # Convert to PoseResult format
            poses = []
            h, w = frame.shape[:2]

            # Limit to max_persons
            person_predictions = predictions[0][:self._max_persons]

            for pred in person_predictions:
                keypoints = pred.get('keypoints', [])
                kpt_scores = pred.get('keypoint_scores', [])

                if len(keypoints) < NUM_KEYPOINTS:
                    continue

                # Convert to Landmark list
                landmarks = []
                for i in range(NUM_KEYPOINTS):
                    landmarks.append(
                        Landmark(
                            x=float(keypoints[i][0] / w),  # Normalize to 0-1
                            y=float(keypoints[i][1] / h),
                            z=0.0,  # RTMPose is 2D
                            visibility=float(kpt_scores[i]) if i < len(kpt_scores) else 0.0,
                        )
                    )

                # Calculate average confidence
                avg_confidence = float(np.mean(kpt_scores)) if kpt_scores else 0.0

                # Calculate joint angles
                angles = self._calculate_angles(landmarks)

                # Classify pose
                pose_type = self._classify_pose(landmarks, angles)

                pose_result = PoseResult(
                    detected=True,
                    confidence=avg_confidence,
                    landmarks=landmarks,
                    angles=angles,
                    pose_type=pose_type,
                    timestamp=timestamp,
                    frame_number=self._frame_count,
                )
                poses.append(pose_result)

            return MultiPersonPoseResult(poses, timestamp, self._frame_count)

        except Exception as e:
            logger.error(f"RTMPose detection error: {e}", exc_info=True)
            return MultiPersonPoseResult([], timestamp, self._frame_count)

    def _calculate_angles(self, landmarks: List[Landmark]) -> JointAngles:
        """
        Calculate joint angles from COCO 17-point landmarks.

        Uses vector math to calculate angles between body segments.
        """
        if len(landmarks) < NUM_KEYPOINTS:
            return JointAngles()

        def get_angle(p1: Landmark, p2: Landmark, p3: Landmark) -> float:
            """Calculate angle at p2 formed by p1-p2-p3."""
            v1 = np.array([p1.x - p2.x, p1.y - p2.y])
            v2 = np.array([p3.x - p2.x, p3.y - p2.y])

            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0

            cos_angle = np.dot(v1, v2) / (norm1 * norm2)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            return float(np.degrees(np.arccos(cos_angle)))

        # Get landmarks using COCO 17-point indices
        nose = landmarks[BodyPart.NOSE]
        left_shoulder = landmarks[BodyPart.LEFT_SHOULDER]
        right_shoulder = landmarks[BodyPart.RIGHT_SHOULDER]
        left_elbow = landmarks[BodyPart.LEFT_ELBOW]
        right_elbow = landmarks[BodyPart.RIGHT_ELBOW]
        left_wrist = landmarks[BodyPart.LEFT_WRIST]
        right_wrist = landmarks[BodyPart.RIGHT_WRIST]
        left_hip = landmarks[BodyPart.LEFT_HIP]
        right_hip = landmarks[BodyPart.RIGHT_HIP]
        left_knee = landmarks[BodyPart.LEFT_KNEE]
        right_knee = landmarks[BodyPart.RIGHT_KNEE]
        left_ankle = landmarks[BodyPart.LEFT_ANKLE]
        right_ankle = landmarks[BodyPart.RIGHT_ANKLE]

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
            z=0.0,
            visibility=(left_shoulder.visibility + right_shoulder.visibility) / 2,
        )
        mid_hip = Landmark(
            x=(left_hip.x + right_hip.x) / 2,
            y=(left_hip.y + right_hip.y) / 2,
            z=0.0,
            visibility=(left_hip.visibility + right_hip.visibility) / 2,
        )

        dx = mid_shoulder.x - mid_hip.x
        dy = mid_shoulder.y - mid_hip.y
        torso_angle = np.degrees(np.arctan2(dx, -dy))
        angles.torso = float(abs(torso_angle))

        # Neck angle (mid_shoulder to nose vs vertical)
        dx_neck = nose.x - mid_shoulder.x
        dy_neck = nose.y - mid_shoulder.y
        neck_angle = np.degrees(np.arctan2(dx_neck, -dy_neck))
        angles.neck = float(abs(neck_angle))

        return angles

    def _classify_pose(
        self, landmarks: List[Landmark], angles: JointAngles
    ) -> PoseType:
        """
        Classify the detected pose into a type.

        Simple rule-based classification based on joint angles.
        """
        if not angles or len(landmarks) < NUM_KEYPOINTS:
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
        # Brace position: knees ~90 deg, torso forward, arms bent
        if 70 <= avg_knee <= 110 and torso > 20:
            left_elbow = angles.left_elbow or 180
            right_elbow = angles.right_elbow or 180
            avg_elbow = (left_elbow + right_elbow) / 2
            if avg_elbow < 120:
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
            for start_part, end_part in POSE_CONNECTIONS:
                start_lm = result.get_landmark(start_part)
                end_lm = result.get_landmark(end_part)

                if start_lm and end_lm:
                    if start_lm.visibility > 0.3 and end_lm.visibility > 0.3:
                        start_pt = start_lm.to_pixel(w, h)
                        end_pt = end_lm.to_pixel(w, h)
                        cv2.line(output, start_pt, end_pt, (0, 212, 255), 2)

        # Draw landmarks
        for lm in result.landmarks:
            if lm.visibility > 0.3:
                pt = lm.to_pixel(w, h)
                cv2.circle(output, pt, 4, (0, 255, 0), -1)
                cv2.circle(output, pt, 6, (0, 212, 255), 1)

        return output

    def draw_multi_landmarks(
        self,
        frame: np.ndarray,
        result: MultiPersonPoseResult,
        draw_connections: bool = True,
    ) -> np.ndarray:
        """
        Draw landmarks for all detected persons.

        Args:
            frame: BGR image to draw on
            result: MultiPersonPoseResult from detect_multi()
            draw_connections: Whether to draw skeleton connections

        Returns:
            Frame with all landmarks drawn
        """
        output = frame.copy()
        for pose in result.poses:
            output = self.draw_landmarks(output, pose, draw_connections)
        return output

    def release(self) -> None:
        """Release MMPose resources and clear GPU memory."""
        self._inferencer = None
        self._is_initialized = False

        # Clear CUDA cache
        if "cuda" in self._device:
            try:
                import torch

                torch.cuda.empty_cache()
            except ImportError:
                pass

    @property
    def device(self) -> str:
        """Get current device."""
        return self._device

    @property
    def max_persons(self) -> int:
        """Get maximum persons to detect."""
        return self._max_persons
