"""
Pose Analyzer - Joint angle calculation and pose analysis.

Provides detailed analysis of body pose including angle calculations,
symmetry analysis, and pose stability metrics.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.perception.pose_detector import (
    BodyPart,
    JointAngles,
    Landmark,
    NUM_KEYPOINTS,
    PoseResult,
    PoseType,
)


@dataclass
class AngleDeviation:
    """Deviation from target angle."""

    joint_name: str
    current_angle: float
    target_angle: float
    deviation: float  # Absolute deviation
    is_within_tolerance: bool
    tolerance: float


@dataclass
class SymmetryAnalysis:
    """Analysis of body symmetry."""

    is_symmetric: bool
    left_right_diff: Dict[str, float]  # Joint name -> difference
    overall_symmetry_score: float  # 0-1, higher is more symmetric


@dataclass
class PoseStability:
    """Pose stability over time."""

    is_stable: bool
    stability_score: float  # 0-1
    movement_magnitude: float  # Average pixel movement
    stable_duration: float  # Seconds pose has been stable


@dataclass
class PoseAnalysisResult:
    """Complete pose analysis result."""

    pose_result: PoseResult
    angle_deviations: List[AngleDeviation]
    symmetry: SymmetryAnalysis
    stability: Optional[PoseStability]
    overall_score: float  # 0-100
    feedback: List[str]  # Human-readable feedback


class PoseAnalyzer:
    """
    Analyzes pose results for compliance and quality.

    Provides:
    - Joint angle calculations
    - Angle deviation from targets
    - Body symmetry analysis
    - Pose stability tracking
    - Overall scoring

    Usage:
        analyzer = PoseAnalyzer()
        result = detector.detect(frame)
        analysis = analyzer.analyze(result)
        print(f"Score: {analysis.overall_score}")
        for feedback in analysis.feedback:
            print(f"  - {feedback}")
    """

    # Default target angles for good posture
    DEFAULT_TARGETS = {
        "left_knee": 90.0,
        "right_knee": 90.0,
        "left_elbow": 90.0,
        "right_elbow": 90.0,
        "torso": 0.0,  # Upright
    }

    # Default tolerances (degrees)
    DEFAULT_TOLERANCES = {
        "left_knee": 15.0,
        "right_knee": 15.0,
        "left_elbow": 20.0,
        "right_elbow": 20.0,
        "torso": 10.0,
    }

    def __init__(
        self,
        target_angles: Optional[Dict[str, float]] = None,
        tolerances: Optional[Dict[str, float]] = None,
        stability_threshold: float = 0.02,  # 2% of frame dimension
        stability_window: int = 10,  # Number of frames
    ) -> None:
        """
        Initialize pose analyzer.

        Args:
            target_angles: Target angles for each joint
            tolerances: Tolerance for each joint angle
            stability_threshold: Movement threshold for stability
            stability_window: Number of frames for stability calculation
        """
        self._target_angles = target_angles or self.DEFAULT_TARGETS.copy()
        self._tolerances = tolerances or self.DEFAULT_TOLERANCES.copy()
        self._stability_threshold = stability_threshold
        self._stability_window = stability_window

        # History for stability calculation
        self._pose_history: List[PoseResult] = []
        self._stable_start_time: Optional[float] = None

    def analyze(
        self,
        pose_result: PoseResult,
        target_angles: Optional[Dict[str, float]] = None,
    ) -> PoseAnalysisResult:
        """
        Perform complete pose analysis.

        Args:
            pose_result: PoseResult from detector
            target_angles: Optional override for target angles

        Returns:
            PoseAnalysisResult with all analysis data
        """
        targets = target_angles or self._target_angles

        # Calculate angle deviations
        deviations = self._calculate_deviations(pose_result, targets)

        # Analyze symmetry
        symmetry = self._analyze_symmetry(pose_result)

        # Track stability
        stability = self._track_stability(pose_result)

        # Calculate overall score
        score = self._calculate_score(deviations, symmetry, stability)

        # Generate feedback
        feedback = self._generate_feedback(deviations, symmetry, stability)

        return PoseAnalysisResult(
            pose_result=pose_result,
            angle_deviations=deviations,
            symmetry=symmetry,
            stability=stability,
            overall_score=score,
            feedback=feedback,
        )

    def calculate_angle(
        self,
        p1: Landmark,
        p2: Landmark,
        p3: Landmark,
    ) -> float:
        """
        Calculate angle at p2 formed by points p1-p2-p3.

        Args:
            p1: First point
            p2: Vertex point (angle measured here)
            p3: Third point

        Returns:
            Angle in degrees (0-180)
        """
        v1 = np.array([p1.x - p2.x, p1.y - p2.y, p1.z - p2.z])
        v2 = np.array([p3.x - p2.x, p3.y - p2.y, p3.z - p2.z])

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        cos_angle = np.dot(v1, v2) / (norm1 * norm2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)

        return float(np.degrees(np.arccos(cos_angle)))

    def calculate_angle_2d(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
    ) -> float:
        """
        Calculate 2D angle at p2 formed by points p1-p2-p3.

        Args:
            p1: First point (x, y)
            p2: Vertex point (x, y)
            p3: Third point (x, y)

        Returns:
            Angle in degrees (0-180)
        """
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        cos_angle = np.dot(v1, v2) / (norm1 * norm2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)

        return float(np.degrees(np.arccos(cos_angle)))

    def get_body_lean_angle(self, pose_result: PoseResult) -> float:
        """
        Calculate the body lean angle from vertical.

        Args:
            pose_result: PoseResult with landmarks

        Returns:
            Lean angle in degrees (0 = upright)
        """
        if not pose_result.detected or len(pose_result.landmarks) < NUM_KEYPOINTS:
            return 0.0

        left_shoulder = pose_result.get_landmark(BodyPart.LEFT_SHOULDER)
        right_shoulder = pose_result.get_landmark(BodyPart.RIGHT_SHOULDER)
        left_hip = pose_result.get_landmark(BodyPart.LEFT_HIP)
        right_hip = pose_result.get_landmark(BodyPart.RIGHT_HIP)

        if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
            return 0.0

        # Calculate midpoints
        mid_shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
        mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        mid_hip_x = (left_hip.x + right_hip.x) / 2
        mid_hip_y = (left_hip.y + right_hip.y) / 2

        # Calculate angle from vertical
        dx = mid_shoulder_x - mid_hip_x
        dy = mid_shoulder_y - mid_hip_y

        # Note: y increases downward in image coordinates
        angle = np.degrees(np.arctan2(dx, -dy))
        return float(abs(angle))

    def _calculate_deviations(
        self,
        pose_result: PoseResult,
        targets: Dict[str, float],
    ) -> List[AngleDeviation]:
        """Calculate deviations from target angles."""
        deviations = []

        if not pose_result.detected or pose_result.angles is None:
            return deviations

        angles_dict = pose_result.angles.to_dict()

        for joint_name, target in targets.items():
            current = angles_dict.get(joint_name)
            if current is None:
                continue

            tolerance = self._tolerances.get(joint_name, 15.0)
            deviation = abs(current - target)
            is_within = deviation <= tolerance

            deviations.append(
                AngleDeviation(
                    joint_name=joint_name,
                    current_angle=current,
                    target_angle=target,
                    deviation=deviation,
                    is_within_tolerance=is_within,
                    tolerance=tolerance,
                )
            )

        return deviations

    def _analyze_symmetry(self, pose_result: PoseResult) -> SymmetryAnalysis:
        """Analyze body symmetry."""
        if not pose_result.detected or pose_result.angles is None:
            return SymmetryAnalysis(
                is_symmetric=False,
                left_right_diff={},
                overall_symmetry_score=0.0,
            )

        angles = pose_result.angles
        differences = {}

        # Compare left/right pairs
        pairs = [
            ("elbow", angles.left_elbow, angles.right_elbow),
            ("shoulder", angles.left_shoulder, angles.right_shoulder),
            ("knee", angles.left_knee, angles.right_knee),
            ("hip", angles.left_hip, angles.right_hip),
        ]

        total_diff = 0.0
        count = 0

        for name, left, right in pairs:
            if left is not None and right is not None:
                diff = abs(left - right)
                differences[name] = diff
                total_diff += diff
                count += 1

        # Calculate symmetry score (inversely proportional to difference)
        if count > 0:
            avg_diff = total_diff / count
            # Score decreases as difference increases
            # Perfect symmetry (0 diff) = 1.0
            # 30+ degrees difference = 0.0
            symmetry_score = max(0.0, 1.0 - (avg_diff / 30.0))
        else:
            symmetry_score = 0.0

        is_symmetric = symmetry_score > 0.7  # 70% threshold

        return SymmetryAnalysis(
            is_symmetric=is_symmetric,
            left_right_diff=differences,
            overall_symmetry_score=symmetry_score,
        )

    def _track_stability(self, pose_result: PoseResult) -> PoseStability:
        """Track pose stability over time."""
        # Add to history
        self._pose_history.append(pose_result)

        # Keep only recent history
        if len(self._pose_history) > self._stability_window:
            self._pose_history.pop(0)

        if len(self._pose_history) < 2:
            return PoseStability(
                is_stable=False,
                stability_score=0.0,
                movement_magnitude=0.0,
                stable_duration=0.0,
            )

        # Calculate movement between frames
        movements = []
        for i in range(1, len(self._pose_history)):
            prev = self._pose_history[i - 1]
            curr = self._pose_history[i]

            if prev.detected and curr.detected:
                # Calculate average landmark movement
                prev_arr = prev.get_landmarks_array()
                curr_arr = curr.get_landmarks_array()

                if len(prev_arr) > 0 and len(curr_arr) > 0:
                    diff = np.abs(curr_arr - prev_arr)
                    avg_movement = float(np.mean(diff))
                    movements.append(avg_movement)

        if not movements:
            return PoseStability(
                is_stable=False,
                stability_score=0.0,
                movement_magnitude=0.0,
                stable_duration=0.0,
            )

        avg_movement = np.mean(movements)
        is_stable = avg_movement < self._stability_threshold

        # Update stable duration tracking
        if is_stable:
            if self._stable_start_time is None:
                self._stable_start_time = pose_result.timestamp
            stable_duration = pose_result.timestamp - self._stable_start_time
        else:
            self._stable_start_time = None
            stable_duration = 0.0

        # Calculate stability score
        # Lower movement = higher score
        stability_score = max(0.0, 1.0 - (avg_movement / self._stability_threshold))
        stability_score = min(1.0, stability_score)

        return PoseStability(
            is_stable=is_stable,
            stability_score=stability_score,
            movement_magnitude=float(avg_movement),
            stable_duration=stable_duration,
        )

    def _calculate_score(
        self,
        deviations: List[AngleDeviation],
        symmetry: SymmetryAnalysis,
        stability: Optional[PoseStability],
    ) -> float:
        """Calculate overall pose score (0-100)."""
        if not deviations:
            return 0.0

        # Angle compliance score (50% weight)
        within_tolerance = sum(1 for d in deviations if d.is_within_tolerance)
        angle_score = (within_tolerance / len(deviations)) * 50 if deviations else 0

        # Symmetry score (25% weight)
        symmetry_score = symmetry.overall_symmetry_score * 25

        # Stability score (25% weight)
        stability_score = 0.0
        if stability:
            stability_score = stability.stability_score * 25

        return angle_score + symmetry_score + stability_score

    def _generate_feedback(
        self,
        deviations: List[AngleDeviation],
        symmetry: SymmetryAnalysis,
        stability: Optional[PoseStability],
    ) -> List[str]:
        """Generate human-readable feedback."""
        feedback = []

        # Angle feedback
        for dev in deviations:
            if not dev.is_within_tolerance:
                if dev.current_angle > dev.target_angle:
                    direction = "过大"
                else:
                    direction = "过小"

                joint_names_cn = {
                    "left_knee": "左膝",
                    "right_knee": "右膝",
                    "left_elbow": "左肘",
                    "right_elbow": "右肘",
                    "torso": "躯干",
                    "left_shoulder": "左肩",
                    "right_shoulder": "右肩",
                    "left_hip": "左髋",
                    "right_hip": "右髋",
                }
                joint_cn = joint_names_cn.get(dev.joint_name, dev.joint_name)
                feedback.append(
                    f"{joint_cn}角度{direction} (当前:{dev.current_angle:.1f}°, "
                    f"目标:{dev.target_angle:.1f}°)"
                )

        # Symmetry feedback
        if not symmetry.is_symmetric:
            max_diff_joint = max(
                symmetry.left_right_diff.items(),
                key=lambda x: x[1],
                default=("", 0),
            )
            if max_diff_joint[1] > 10:
                joint_names_cn = {
                    "elbow": "肘部",
                    "shoulder": "肩部",
                    "knee": "膝部",
                    "hip": "髋部",
                }
                joint_cn = joint_names_cn.get(max_diff_joint[0], max_diff_joint[0])
                feedback.append(f"左右{joint_cn}不对称 (差异:{max_diff_joint[1]:.1f}°)")

        # Stability feedback
        if stability and not stability.is_stable:
            feedback.append("姿势不够稳定，请保持静止")

        return feedback

    def reset_history(self) -> None:
        """Reset pose history for stability tracking."""
        self._pose_history.clear()
        self._stable_start_time = None
