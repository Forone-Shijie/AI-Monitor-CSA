"""
Pose Scorer - Evaluates posture compliance and generates scores.

Analyzes pose data against standards to calculate:
- Joint angle deviations
- Body alignment scores
- Posture stability metrics
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class PostureCategory(Enum):
    """Categories of posture evaluation."""

    TORSO = "torso"  # Trunk and back alignment
    HEAD = "head"  # Head and neck position
    ARMS = "arms"  # Upper limb positioning
    LEGS = "legs"  # Lower limb positioning
    OVERALL = "overall"  # Overall body posture


@dataclass
class AngleScore:
    """Score for a specific joint angle."""

    joint_name: str
    target_angle: float
    actual_angle: float
    deviation: float
    score: float  # 0-100
    feedback: str = ""


@dataclass
class CategoryScore:
    """Score for a posture category."""

    category: PostureCategory
    score: float  # 0-100
    weight: float  # Category weight
    weighted_score: float
    angle_scores: List[AngleScore] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)


@dataclass
class PoseScoreResult:
    """Complete pose scoring result."""

    # Overall score
    total_score: float  # 0-100
    grade: str  # A/B/C/D/F

    # Category scores
    category_scores: Dict[PostureCategory, CategoryScore] = field(
        default_factory=dict
    )

    # Detailed feedback
    strengths: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)

    # Timing
    evaluation_time: float = 0.0
    hold_duration: float = 0.0
    stability_score: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "total_score": self.total_score,
            "grade": self.grade,
            "category_scores": {
                cat.value: {
                    "score": cs.score,
                    "weight": cs.weight,
                    "weighted_score": cs.weighted_score,
                    "feedback": cs.feedback,
                }
                for cat, cs in self.category_scores.items()
            },
            "strengths": self.strengths,
            "improvements": self.improvements,
            "hold_duration": self.hold_duration,
            "stability_score": self.stability_score,
        }


class PoseScorer:
    """
    Pose scoring engine for evaluating posture compliance.

    Evaluates poses against defined standards and generates scores
    based on joint angle deviations and body alignment.

    Usage:
        scorer = PoseScorer()

        # Configure for brace position
        scorer.set_scenario("brace_position")

        # Score a pose
        result = scorer.score(pose_analysis_result)
        print(f"Score: {result.total_score}, Grade: {result.grade}")

        # Score with stability
        result = scorer.score_with_history(pose_history)
    """

    # Default category weights (must sum to 1.0)
    DEFAULT_WEIGHTS = {
        PostureCategory.TORSO: 0.30,
        PostureCategory.HEAD: 0.20,
        PostureCategory.ARMS: 0.25,
        PostureCategory.LEGS: 0.25,
    }

    # Grade thresholds
    GRADE_THRESHOLDS = [
        (90, "A"),
        (80, "B"),
        (70, "C"),
        (60, "D"),
        (0, "F"),
    ]

    # Scenario-specific standards
    SCENARIO_STANDARDS = {
        "brace_position": {
            PostureCategory.TORSO: {
                "spine_angle": {"target": 45.0, "tolerance": 15.0, "weight": 1.0},
            },
            PostureCategory.HEAD: {
                "head_tilt": {"target": -30.0, "tolerance": 20.0, "weight": 1.0},
            },
            PostureCategory.ARMS: {
                "elbow_angle": {"target": 90.0, "tolerance": 30.0, "weight": 0.5},
                "shoulder_angle": {"target": 45.0, "tolerance": 20.0, "weight": 0.5},
            },
            PostureCategory.LEGS: {
                "knee_angle": {"target": 90.0, "tolerance": 15.0, "weight": 0.6},
                "hip_angle": {"target": 90.0, "tolerance": 20.0, "weight": 0.4},
            },
        },
        "standing": {
            PostureCategory.TORSO: {
                "spine_angle": {"target": 0.0, "tolerance": 10.0, "weight": 1.0},
            },
            PostureCategory.HEAD: {
                "head_tilt": {"target": 0.0, "tolerance": 10.0, "weight": 1.0},
            },
            PostureCategory.ARMS: {
                "elbow_angle": {"target": 170.0, "tolerance": 20.0, "weight": 1.0},
            },
            PostureCategory.LEGS: {
                "knee_angle": {"target": 175.0, "tolerance": 10.0, "weight": 1.0},
            },
        },
    }

    def __init__(
        self,
        scenario: str = "brace_position",
        weights: Optional[Dict[PostureCategory, float]] = None,
    ) -> None:
        """
        Initialize pose scorer.

        Args:
            scenario: Scenario name for standards
            weights: Optional custom category weights
        """
        self._scenario = scenario
        self._weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._standards = self.SCENARIO_STANDARDS.get(scenario, {})
        self._pose_history: List[Dict] = []

    def set_scenario(self, scenario: str) -> None:
        """Set the evaluation scenario."""
        self._scenario = scenario
        self._standards = self.SCENARIO_STANDARDS.get(scenario, {})

    def set_weights(self, weights: Dict[PostureCategory, float]) -> None:
        """Set category weights."""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            # Normalize weights
            self._weights = {k: v / total for k, v in weights.items()}
        else:
            self._weights = weights.copy()

    def add_custom_standard(
        self,
        scenario: str,
        category: PostureCategory,
        joint_name: str,
        target: float,
        tolerance: float,
        weight: float = 1.0,
    ) -> None:
        """Add or update a custom standard."""
        if scenario not in self.SCENARIO_STANDARDS:
            self.SCENARIO_STANDARDS[scenario] = {}

        if category not in self.SCENARIO_STANDARDS[scenario]:
            self.SCENARIO_STANDARDS[scenario][category] = {}

        self.SCENARIO_STANDARDS[scenario][category][joint_name] = {
            "target": target,
            "tolerance": tolerance,
            "weight": weight,
        }

        if scenario == self._scenario:
            self._standards = self.SCENARIO_STANDARDS[scenario]

    def score(
        self,
        pose_data: Any,
        brace_result: Optional[Any] = None,
    ) -> PoseScoreResult:
        """
        Score a single pose.

        Args:
            pose_data: PoseAnalysisResult or dict with angle data
            brace_result: Optional BracePositionResult for additional context

        Returns:
            PoseScoreResult with detailed scoring
        """
        category_scores = {}

        for category in PostureCategory:
            if category == PostureCategory.OVERALL:
                continue

            cat_score = self._score_category(category, pose_data, brace_result)
            category_scores[category] = cat_score

        # Calculate total score
        total_score = sum(
            cs.weighted_score for cs in category_scores.values()
        )

        # Determine grade
        grade = self._calculate_grade(total_score)

        # Generate feedback
        strengths, improvements = self._generate_feedback(category_scores)

        return PoseScoreResult(
            total_score=total_score,
            grade=grade,
            category_scores=category_scores,
            strengths=strengths,
            improvements=improvements,
        )

    def score_with_history(
        self,
        pose_history: List[Any],
        min_hold_duration: float = 5.0,
    ) -> PoseScoreResult:
        """
        Score poses with stability analysis.

        Args:
            pose_history: List of pose data over time
            min_hold_duration: Minimum hold duration required

        Returns:
            PoseScoreResult with stability metrics
        """
        if not pose_history:
            return PoseScoreResult(
                total_score=0.0,
                grade="F",
                improvements=["未检测到姿势数据"],
            )

        # Score each pose
        scores = [self.score(pose) for pose in pose_history]

        # Calculate average score
        avg_score = np.mean([s.total_score for s in scores])

        # Calculate stability (variance of scores)
        score_variance = np.var([s.total_score for s in scores])
        stability_score = max(0, 100 - score_variance * 2)

        # Estimate hold duration
        hold_duration = len(pose_history) * 0.033  # Assuming ~30fps

        # Final score considers stability
        stability_weight = 0.2
        pose_weight = 0.8
        final_score = (
            avg_score * pose_weight + stability_score * stability_weight
        )

        # Get the best individual result for category details
        best_result = max(scores, key=lambda x: x.total_score)

        # Add stability feedback
        improvements = best_result.improvements.copy()
        if stability_score < 80:
            improvements.append("姿势保持稳定性需要提高")
        if hold_duration < min_hold_duration:
            improvements.append(
                f"姿势保持时间 {hold_duration:.1f}秒，未达到 {min_hold_duration:.0f}秒 要求"
            )

        return PoseScoreResult(
            total_score=final_score,
            grade=self._calculate_grade(final_score),
            category_scores=best_result.category_scores,
            strengths=best_result.strengths,
            improvements=improvements,
            hold_duration=hold_duration,
            stability_score=stability_score,
        )

    def _score_category(
        self,
        category: PostureCategory,
        pose_data: Any,
        brace_result: Optional[Any],
    ) -> CategoryScore:
        """Score a single category."""
        standards = self._standards.get(category, {})
        weight = self._weights.get(category, 0.25)

        if not standards:
            return CategoryScore(
                category=category,
                score=100.0,
                weight=weight,
                weighted_score=100.0 * weight,
            )

        angle_scores = []
        total_weighted = 0.0
        total_weight = 0.0

        for joint_name, standard in standards.items():
            actual_angle = self._get_angle_from_data(
                joint_name, pose_data, brace_result
            )

            if actual_angle is None:
                continue

            target = standard["target"]
            tolerance = standard["tolerance"]
            joint_weight = standard.get("weight", 1.0)

            deviation = abs(actual_angle - target)
            joint_score = self._calculate_angle_score(deviation, tolerance)

            feedback = self._generate_angle_feedback(
                joint_name, deviation, tolerance, joint_score
            )

            angle_scores.append(
                AngleScore(
                    joint_name=joint_name,
                    target_angle=target,
                    actual_angle=actual_angle,
                    deviation=deviation,
                    score=joint_score,
                    feedback=feedback,
                )
            )

            total_weighted += joint_score * joint_weight
            total_weight += joint_weight

        if total_weight > 0:
            category_score = total_weighted / total_weight
        else:
            category_score = 100.0

        # Generate category feedback
        category_feedback = [
            as_.feedback for as_ in angle_scores if as_.score < 80
        ]

        return CategoryScore(
            category=category,
            score=category_score,
            weight=weight,
            weighted_score=category_score * weight,
            angle_scores=angle_scores,
            feedback=category_feedback,
        )

    def _get_angle_from_data(
        self,
        joint_name: str,
        pose_data: Any,
        brace_result: Optional[Any],
    ) -> Optional[float]:
        """Extract angle value from pose data."""
        # Try to get from pose_data
        if hasattr(pose_data, "angles") and pose_data.angles:
            angles = pose_data.angles
            if hasattr(angles, joint_name):
                return getattr(angles, joint_name)
            if isinstance(angles, dict) and joint_name in angles:
                return angles[joint_name]

        # Try dict access
        if isinstance(pose_data, dict):
            if "angles" in pose_data:
                angles = pose_data["angles"]
                if isinstance(angles, dict) and joint_name in angles:
                    return angles[joint_name]
            if joint_name in pose_data:
                return pose_data[joint_name]

        # Try brace result
        if brace_result:
            if hasattr(brace_result, "body_lean_angle"):
                if joint_name == "spine_angle":
                    return brace_result.body_lean_angle
            if isinstance(brace_result, dict):
                if joint_name in brace_result:
                    return brace_result[joint_name]

        return None

    def _calculate_angle_score(
        self,
        deviation: float,
        tolerance: float,
    ) -> float:
        """Calculate score based on deviation from target."""
        if deviation <= tolerance * 0.5:
            return 100.0
        elif deviation <= tolerance:
            # Linear decrease from 100 to 80
            ratio = (deviation - tolerance * 0.5) / (tolerance * 0.5)
            return 100.0 - ratio * 20.0
        elif deviation <= tolerance * 2:
            # Steeper decrease from 80 to 50
            ratio = (deviation - tolerance) / tolerance
            return 80.0 - ratio * 30.0
        else:
            # Below 50 for severe deviations
            ratio = min(1.0, (deviation - tolerance * 2) / tolerance)
            return max(0.0, 50.0 - ratio * 50.0)

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"

    def _generate_angle_feedback(
        self,
        joint_name: str,
        deviation: float,
        tolerance: float,
        score: float,
    ) -> str:
        """Generate feedback for a specific angle."""
        joint_names_cn = {
            "spine_angle": "脊柱角度",
            "head_tilt": "头部倾斜",
            "elbow_angle": "肘部角度",
            "shoulder_angle": "肩部角度",
            "knee_angle": "膝盖角度",
            "hip_angle": "髋部角度",
        }

        name = joint_names_cn.get(joint_name, joint_name)

        if score >= 90:
            return f"{name}标准"
        elif score >= 70:
            return f"{name}偏差{deviation:.1f}°，轻微调整"
        elif score >= 50:
            return f"{name}偏差{deviation:.1f}°，需要纠正"
        else:
            return f"{name}偏差{deviation:.1f}°，严重不合规"

    def _generate_feedback(
        self,
        category_scores: Dict[PostureCategory, CategoryScore],
    ) -> Tuple[List[str], List[str]]:
        """Generate overall feedback."""
        strengths = []
        improvements = []

        category_names = {
            PostureCategory.TORSO: "躯干姿态",
            PostureCategory.HEAD: "头部位置",
            PostureCategory.ARMS: "手臂姿态",
            PostureCategory.LEGS: "腿部姿态",
        }

        for category, cat_score in category_scores.items():
            name = category_names.get(category, category.value)

            if cat_score.score >= 90:
                strengths.append(f"{name}优秀")
            elif cat_score.score >= 80:
                strengths.append(f"{name}良好")
            elif cat_score.score < 70:
                improvements.extend(cat_score.feedback)
                if not cat_score.feedback:
                    improvements.append(f"{name}需要改进")

        return strengths, improvements

    def reset_history(self) -> None:
        """Reset pose history."""
        self._pose_history.clear()

    @property
    def scenario(self) -> str:
        """Get current scenario."""
        return self._scenario

    @property
    def weights(self) -> Dict[PostureCategory, float]:
        """Get current weights."""
        return self._weights.copy()
