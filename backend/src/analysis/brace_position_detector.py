"""
Brace Position Detector - Detects cabin crew brace/impact position compliance.

Monitors the four key body parts for brace position:
1. Torso & Back - Forward lean angle
2. Head & Neck - Proper positioning (facing forward/rear)
3. Arms & Hands - Crossed arms or hands on thighs
4. Legs & Feet - Knee angle 85-95°, feet flat

Reference: Aviation safety brace position standards
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.perception.pose_detector import (
    BodyPart,
    Landmark,
    NUM_KEYPOINTS,
    PoseResult,
)


class HeadPosition(Enum):
    """Head position mode for brace position."""

    FORWARD = "forward"  # Head facing forward (standard)
    REAR = "rear"  # Head facing rear (alternative)
    UNKNOWN = "unknown"


class ArmPosition(Enum):
    """Arm position mode for brace position."""

    CROSSED = "crossed"  # Arms crossed over chest
    ON_THIGHS = "on_thighs"  # Hands on thighs
    UNKNOWN = "unknown"


@dataclass
class BodyPartStatus:
    """Status of a single body part for brace position."""

    part_name: str  # Body part name
    part_name_cn: str  # Chinese name
    is_compliant: bool  # Whether within acceptable range
    current_value: float  # Current measured value
    target_range: Tuple[float, float]  # (min, max) target range
    deviation: float  # Deviation from target (0 if compliant)
    confidence: float  # Detection confidence for this part
    feedback: str  # Specific feedback for this part


@dataclass
class BracePositionResult:
    """Complete brace position detection result."""

    # Detection status
    detected: bool  # Whether pose was detected
    timestamp: float  # Detection timestamp

    # Body part statuses
    torso: BodyPartStatus  # Torso & back status
    head: BodyPartStatus  # Head & neck status
    arms: BodyPartStatus  # Arms & hands status
    legs: BodyPartStatus  # Legs & feet status

    # Overall assessment
    is_complete: bool  # All parts compliant
    compliance_ratio: float  # Ratio of compliant parts (0-1)
    stability_score: float  # Pose stability (0-1)

    # Timing
    time_to_position: Optional[float] = None  # Seconds to achieve position
    hold_duration: float = 0.0  # Seconds position has been held

    # Overall feedback
    overall_feedback: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "detected": self.detected,
            "timestamp": self.timestamp,
            "torso": {
                "part_name": self.torso.part_name,
                "is_compliant": self.torso.is_compliant,
                "current_value": self.torso.current_value,
                "target_range": self.torso.target_range,
                "deviation": self.torso.deviation,
                "feedback": self.torso.feedback,
            },
            "head": {
                "part_name": self.head.part_name,
                "is_compliant": self.head.is_compliant,
                "current_value": self.head.current_value,
                "target_range": self.head.target_range,
                "deviation": self.head.deviation,
                "feedback": self.head.feedback,
            },
            "arms": {
                "part_name": self.arms.part_name,
                "is_compliant": self.arms.is_compliant,
                "current_value": self.arms.current_value,
                "target_range": self.arms.target_range,
                "deviation": self.arms.deviation,
                "feedback": self.arms.feedback,
            },
            "legs": {
                "part_name": self.legs.part_name,
                "is_compliant": self.legs.is_compliant,
                "current_value": self.legs.current_value,
                "target_range": self.legs.target_range,
                "deviation": self.legs.deviation,
                "feedback": self.legs.feedback,
            },
            "is_complete": self.is_complete,
            "compliance_ratio": self.compliance_ratio,
            "stability_score": self.stability_score,
            "time_to_position": self.time_to_position,
            "hold_duration": self.hold_duration,
            "overall_feedback": self.overall_feedback,
        }


class BracePositionDetector:
    """
    Detects and evaluates brace/impact position for cabin crew training.

    The brace position is a safety position used by cabin crew during
    emergency landings. This detector evaluates four key body parts:

    1. **Torso & Back**: Should lean forward 20-45 degrees
    2. **Head & Neck**: Positioned safely (forward or rear facing)
    3. **Arms & Hands**: Either crossed over chest or on thighs
    4. **Legs & Feet**: Knees at 85-95°, feet flat on floor

    Usage:
        detector = BracePositionDetector()

        # Start monitoring (records trigger time)
        detector.start_monitoring()

        # Detect brace position
        result = detector.detect(pose_result)

        if result.is_complete:
            print(f"Brace position achieved in {result.time_to_position:.1f}s")
            print(f"Holding for {result.hold_duration:.1f}s")

        # Stop monitoring
        detector.stop_monitoring()
    """

    # Configuration defaults
    DEFAULT_CONFIG = {
        # Torso lean angle (degrees from vertical)
        "torso_min_angle": 20.0,
        "torso_max_angle": 45.0,
        "torso_tolerance": 5.0,
        # Knee angle (degrees)
        "knee_min_angle": 85.0,
        "knee_max_angle": 95.0,
        "knee_tolerance": 10.0,
        # Elbow angle for crossed arms (degrees)
        "elbow_crossed_max": 90.0,
        # Head/neck angle tolerance
        "head_max_deviation": 15.0,
        # Stability threshold
        "stability_threshold": 0.02,
        # Time limits
        "max_time_to_position": 5.0,  # seconds
        "min_hold_duration": 30.0,  # seconds
    }

    def __init__(
        self,
        config: Optional[Dict] = None,
        head_mode: HeadPosition = HeadPosition.FORWARD,
        arm_mode: ArmPosition = ArmPosition.CROSSED,
    ) -> None:
        """
        Initialize brace position detector.

        Args:
            config: Configuration overrides
            head_mode: Expected head position mode
            arm_mode: Expected arm position mode
        """
        self._config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._head_mode = head_mode
        self._arm_mode = arm_mode

        # Monitoring state
        self._is_monitoring = False
        self._trigger_time: Optional[float] = None
        self._position_achieved_time: Optional[float] = None

        # History for stability
        self._result_history: List[BracePositionResult] = []
        self._stability_window = 10

    def start_monitoring(self) -> None:
        """Start monitoring for brace position (records trigger time)."""
        self._is_monitoring = True
        self._trigger_time = time.time()
        self._position_achieved_time = None
        self._result_history.clear()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._is_monitoring = False

    def detect(self, pose_result: PoseResult) -> BracePositionResult:
        """
        Detect brace position from pose result.

        Args:
            pose_result: PoseResult from pose detector

        Returns:
            BracePositionResult with all body part statuses
        """
        timestamp = time.time()

        # Check if pose was detected (COCO 17-point format)
        if not pose_result.detected or len(pose_result.landmarks) < NUM_KEYPOINTS:
            return self._create_empty_result(timestamp)

        # Analyze each body part
        torso_status = self._analyze_torso(pose_result)
        head_status = self._analyze_head(pose_result)
        arms_status = self._analyze_arms(pose_result)
        legs_status = self._analyze_legs(pose_result)

        # Calculate overall compliance
        compliant_parts = sum([
            torso_status.is_compliant,
            head_status.is_compliant,
            arms_status.is_compliant,
            legs_status.is_compliant,
        ])
        compliance_ratio = compliant_parts / 4.0
        is_complete = compliant_parts == 4

        # Calculate stability
        stability_score = self._calculate_stability(pose_result)

        # Calculate timing
        time_to_position = None
        hold_duration = 0.0

        if self._is_monitoring and self._trigger_time:
            if is_complete:
                if self._position_achieved_time is None:
                    self._position_achieved_time = timestamp
                    time_to_position = timestamp - self._trigger_time
                else:
                    time_to_position = (
                        self._position_achieved_time - self._trigger_time
                    )
                    hold_duration = timestamp - self._position_achieved_time
            else:
                # Position lost, reset
                self._position_achieved_time = None

        # Generate overall feedback
        overall_feedback = self._generate_overall_feedback(
            torso_status, head_status, arms_status, legs_status,
            is_complete, time_to_position, hold_duration
        )

        result = BracePositionResult(
            detected=True,
            timestamp=timestamp,
            torso=torso_status,
            head=head_status,
            arms=arms_status,
            legs=legs_status,
            is_complete=is_complete,
            compliance_ratio=compliance_ratio,
            stability_score=stability_score,
            time_to_position=time_to_position,
            hold_duration=hold_duration,
            overall_feedback=overall_feedback,
        )

        # Add to history
        self._result_history.append(result)
        if len(self._result_history) > self._stability_window:
            self._result_history.pop(0)

        return result

    def _analyze_torso(self, pose_result: PoseResult) -> BodyPartStatus:
        """Analyze torso/back position."""
        left_shoulder = pose_result.get_landmark(BodyPart.LEFT_SHOULDER)
        right_shoulder = pose_result.get_landmark(BodyPart.RIGHT_SHOULDER)
        left_hip = pose_result.get_landmark(BodyPart.LEFT_HIP)
        right_hip = pose_result.get_landmark(BodyPart.RIGHT_HIP)

        if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
            return self._create_unknown_status("torso", "躯干与背部")

        # Calculate torso lean angle
        mid_shoulder = (
            (left_shoulder.x + right_shoulder.x) / 2,
            (left_shoulder.y + right_shoulder.y) / 2,
        )
        mid_hip = (
            (left_hip.x + right_hip.x) / 2,
            (left_hip.y + right_hip.y) / 2,
        )

        dx = mid_shoulder[0] - mid_hip[0]
        dy = mid_shoulder[1] - mid_hip[1]

        # Angle from vertical (y increases downward)
        lean_angle = abs(np.degrees(np.arctan2(dx, -dy)))

        # Check compliance
        min_angle = self._config["torso_min_angle"]
        max_angle = self._config["torso_max_angle"]
        tolerance = self._config["torso_tolerance"]

        is_compliant = (min_angle - tolerance) <= lean_angle <= (max_angle + tolerance)

        # Calculate deviation
        if lean_angle < min_angle:
            deviation = min_angle - lean_angle
            feedback = f"躯干前倾不足，需再向前倾斜{deviation:.1f}°"
        elif lean_angle > max_angle:
            deviation = lean_angle - max_angle
            feedback = f"躯干前倾过度，需收回{deviation:.1f}°"
        else:
            deviation = 0.0
            feedback = "躯干姿势正确"

        confidence = (left_shoulder.visibility + right_shoulder.visibility +
                      left_hip.visibility + right_hip.visibility) / 4

        return BodyPartStatus(
            part_name="torso",
            part_name_cn="躯干与背部",
            is_compliant=is_compliant,
            current_value=lean_angle,
            target_range=(min_angle, max_angle),
            deviation=deviation,
            confidence=confidence,
            feedback=feedback,
        )

    def _analyze_head(self, pose_result: PoseResult) -> BodyPartStatus:
        """Analyze head/neck position."""
        nose = pose_result.get_landmark(BodyPart.NOSE)
        left_shoulder = pose_result.get_landmark(BodyPart.LEFT_SHOULDER)
        right_shoulder = pose_result.get_landmark(BodyPart.RIGHT_SHOULDER)

        if not all([nose, left_shoulder, right_shoulder]):
            return self._create_unknown_status("head", "头部与颈部")

        # Calculate mid shoulder
        mid_shoulder = (
            (left_shoulder.x + right_shoulder.x) / 2,
            (left_shoulder.y + right_shoulder.y) / 2,
        )

        # Calculate head alignment angle
        dx = nose.x - mid_shoulder[0]
        dy = nose.y - mid_shoulder[1]

        head_angle = abs(np.degrees(np.arctan2(dx, -dy)))

        # Check compliance based on mode
        max_deviation = self._config["head_max_deviation"]

        if self._head_mode == HeadPosition.FORWARD:
            # Head should be roughly aligned with body lean
            is_compliant = head_angle < max_deviation
            target_desc = "头部向前低垂"
        else:  # REAR
            # Head facing rear - different criteria
            is_compliant = head_angle < max_deviation
            target_desc = "头部向后仰靠"

        deviation = max(0, head_angle - max_deviation) if not is_compliant else 0.0

        if is_compliant:
            feedback = "头部位置正确"
        else:
            feedback = f"头部偏离标准位置{deviation:.1f}°，请调整{target_desc}"

        confidence = (nose.visibility + left_shoulder.visibility +
                      right_shoulder.visibility) / 3

        return BodyPartStatus(
            part_name="head",
            part_name_cn="头部与颈部",
            is_compliant=is_compliant,
            current_value=head_angle,
            target_range=(0, max_deviation),
            deviation=deviation,
            confidence=confidence,
            feedback=feedback,
        )

    def _analyze_arms(self, pose_result: PoseResult) -> BodyPartStatus:
        """Analyze arms/hands position."""
        left_shoulder = pose_result.get_landmark(BodyPart.LEFT_SHOULDER)
        right_shoulder = pose_result.get_landmark(BodyPart.RIGHT_SHOULDER)
        left_elbow = pose_result.get_landmark(BodyPart.LEFT_ELBOW)
        right_elbow = pose_result.get_landmark(BodyPart.RIGHT_ELBOW)
        left_wrist = pose_result.get_landmark(BodyPart.LEFT_WRIST)
        right_wrist = pose_result.get_landmark(BodyPart.RIGHT_WRIST)

        required = [left_shoulder, right_shoulder, left_elbow, right_elbow,
                    left_wrist, right_wrist]

        if not all(required):
            return self._create_unknown_status("arms", "上肢与手部")

        # Calculate elbow angles
        left_elbow_angle = self._calculate_angle(
            left_shoulder, left_elbow, left_wrist
        )
        right_elbow_angle = self._calculate_angle(
            right_shoulder, right_elbow, right_wrist
        )
        avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2

        if self._arm_mode == ArmPosition.CROSSED:
            # Arms crossed - elbows should be bent
            max_angle = self._config["elbow_crossed_max"]
            is_compliant = avg_elbow_angle < max_angle

            # Check if wrists are near opposite shoulders (crossed)
            wrist_dist = np.sqrt(
                (left_wrist.x - right_wrist.x) ** 2 +
                (left_wrist.y - right_wrist.y) ** 2
            )
            # Wrists should be close together when crossed
            wrists_crossed = wrist_dist < 0.15  # Normalized distance

            is_compliant = is_compliant and wrists_crossed
            target_desc = "双臂交叉于胸前"
            target_range = (0, max_angle)

        else:  # ON_THIGHS
            # Hands on thighs - arms relatively straight down
            left_hip = pose_result.get_landmark(BodyPart.LEFT_HIP)
            right_hip = pose_result.get_landmark(BodyPart.RIGHT_HIP)

            if left_hip and right_hip:
                # Check if wrists are near hips/thighs
                left_dist = np.sqrt(
                    (left_wrist.x - left_hip.x) ** 2 +
                    (left_wrist.y - left_hip.y) ** 2
                )
                right_dist = np.sqrt(
                    (right_wrist.x - right_hip.x) ** 2 +
                    (right_wrist.y - right_hip.y) ** 2
                )
                hands_on_thighs = left_dist < 0.2 and right_dist < 0.2
                is_compliant = hands_on_thighs
            else:
                is_compliant = False

            target_desc = "双手放于大腿上"
            target_range = (0, 180)

        deviation = max(0, avg_elbow_angle - self._config["elbow_crossed_max"]) \
            if not is_compliant else 0.0

        if is_compliant:
            feedback = "手臂姿势正确"
        else:
            feedback = f"手臂姿势不正确，请{target_desc}"

        confidence = sum(lm.visibility for lm in required) / len(required)

        return BodyPartStatus(
            part_name="arms",
            part_name_cn="上肢与手部",
            is_compliant=is_compliant,
            current_value=avg_elbow_angle,
            target_range=target_range,
            deviation=deviation,
            confidence=confidence,
            feedback=feedback,
        )

    def _analyze_legs(self, pose_result: PoseResult) -> BodyPartStatus:
        """Analyze legs/feet position."""
        left_hip = pose_result.get_landmark(BodyPart.LEFT_HIP)
        right_hip = pose_result.get_landmark(BodyPart.RIGHT_HIP)
        left_knee = pose_result.get_landmark(BodyPart.LEFT_KNEE)
        right_knee = pose_result.get_landmark(BodyPart.RIGHT_KNEE)
        left_ankle = pose_result.get_landmark(BodyPart.LEFT_ANKLE)
        right_ankle = pose_result.get_landmark(BodyPart.RIGHT_ANKLE)

        required = [left_hip, right_hip, left_knee, right_knee,
                    left_ankle, right_ankle]

        if not all(required):
            return self._create_unknown_status("legs", "下肢与脚部")

        # Calculate knee angles
        left_knee_angle = self._calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = self._calculate_angle(right_hip, right_knee, right_ankle)
        avg_knee_angle = (left_knee_angle + right_knee_angle) / 2

        # Check compliance
        min_angle = self._config["knee_min_angle"]
        max_angle = self._config["knee_max_angle"]
        tolerance = self._config["knee_tolerance"]

        is_compliant = (min_angle - tolerance) <= avg_knee_angle <= (max_angle + tolerance)

        # Check feet flat (ankles should be roughly below knees)
        left_flat = abs(left_ankle.x - left_knee.x) < 0.1
        right_flat = abs(right_ankle.x - right_knee.x) < 0.1
        feet_flat = left_flat and right_flat

        is_compliant = is_compliant and feet_flat

        # Calculate deviation
        if avg_knee_angle < min_angle:
            deviation = min_angle - avg_knee_angle
            feedback = f"膝关节弯曲不足，当前{avg_knee_angle:.0f}°，需弯曲至{min_angle:.0f}°-{max_angle:.0f}°"
        elif avg_knee_angle > max_angle:
            deviation = avg_knee_angle - max_angle
            feedback = f"膝关节弯曲过度，当前{avg_knee_angle:.0f}°，需调整至{min_angle:.0f}°-{max_angle:.0f}°"
        elif not feet_flat:
            deviation = 0.0
            feedback = "请将双脚平放在地面上"
        else:
            deviation = 0.0
            feedback = "下肢姿势正确"

        confidence = sum(lm.visibility for lm in required) / len(required)

        return BodyPartStatus(
            part_name="legs",
            part_name_cn="下肢与脚部",
            is_compliant=is_compliant,
            current_value=avg_knee_angle,
            target_range=(min_angle, max_angle),
            deviation=deviation,
            confidence=confidence,
            feedback=feedback,
        )

    def _calculate_angle(
        self,
        p1: Landmark,
        p2: Landmark,
        p3: Landmark,
    ) -> float:
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

    def _calculate_stability(self, pose_result: PoseResult) -> float:
        """Calculate pose stability score."""
        if len(self._result_history) < 2:
            return 0.0

        # Compare current with previous results
        compliance_history = [r.compliance_ratio for r in self._result_history]

        # Stability = consistency of compliance
        if len(compliance_history) >= 2:
            variance = np.var(compliance_history)
            # Lower variance = higher stability
            stability = max(0.0, 1.0 - variance * 10)
        else:
            stability = 0.0

        return float(stability)

    def _generate_overall_feedback(
        self,
        torso: BodyPartStatus,
        head: BodyPartStatus,
        arms: BodyPartStatus,
        legs: BodyPartStatus,
        is_complete: bool,
        time_to_position: Optional[float],
        hold_duration: float,
    ) -> List[str]:
        """Generate overall feedback messages."""
        feedback = []

        if is_complete:
            if time_to_position is not None:
                max_time = self._config["max_time_to_position"]
                if time_to_position <= max_time:
                    feedback.append(f"防冲击姿势到位！用时 {time_to_position:.1f} 秒")
                else:
                    feedback.append(
                        f"防冲击姿势已到位，但用时 {time_to_position:.1f} 秒，"
                        f"超过标准时间 {max_time:.0f} 秒"
                    )

            min_hold = self._config["min_hold_duration"]
            if hold_duration > 0:
                if hold_duration >= min_hold:
                    feedback.append(f"姿势保持良好，已持续 {hold_duration:.1f} 秒")
                else:
                    remaining = min_hold - hold_duration
                    feedback.append(f"请继续保持姿势，还需 {remaining:.1f} 秒")
        else:
            # List non-compliant parts
            non_compliant = []
            if not torso.is_compliant:
                non_compliant.append(torso.part_name_cn)
            if not head.is_compliant:
                non_compliant.append(head.part_name_cn)
            if not arms.is_compliant:
                non_compliant.append(arms.part_name_cn)
            if not legs.is_compliant:
                non_compliant.append(legs.part_name_cn)

            if non_compliant:
                feedback.append(f"需要调整: {', '.join(non_compliant)}")

        return feedback

    def _create_empty_result(self, timestamp: float) -> BracePositionResult:
        """Create empty result when no pose detected."""
        unknown_status = self._create_unknown_status("unknown", "未知")

        return BracePositionResult(
            detected=False,
            timestamp=timestamp,
            torso=unknown_status,
            head=unknown_status,
            arms=unknown_status,
            legs=unknown_status,
            is_complete=False,
            compliance_ratio=0.0,
            stability_score=0.0,
            overall_feedback=["未检测到人体姿态"],
        )

    def _create_unknown_status(self, name: str, name_cn: str) -> BodyPartStatus:
        """Create unknown status for undetected body part."""
        return BodyPartStatus(
            part_name=name,
            part_name_cn=name_cn,
            is_compliant=False,
            current_value=0.0,
            target_range=(0.0, 0.0),
            deviation=0.0,
            confidence=0.0,
            feedback="无法检测该部位",
        )

    @property
    def is_monitoring(self) -> bool:
        """Check if currently monitoring."""
        return self._is_monitoring

    @property
    def trigger_time(self) -> Optional[float]:
        """Get trigger time."""
        return self._trigger_time

    def get_config(self) -> Dict:
        """Get current configuration."""
        return self._config.copy()

    def update_config(self, config: Dict) -> None:
        """Update configuration."""
        self._config.update(config)
