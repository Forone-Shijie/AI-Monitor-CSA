"""
Evaluator - Main evaluation engine combining all scoring dimensions.

Combines pose, action, and communication scores with configurable
weights to produce a comprehensive evaluation result.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .action_scorer import ActionScorer, ActionScoreResult
from .communication_scorer import CommunicationScorer, CommunicationScoreResult
from .pose_scorer import PoseScorer, PoseScoreResult


@dataclass
class EvaluationWeights:
    """Weights for each scoring dimension."""

    pose: float = 0.30  # 30% for posture
    action: float = 0.40  # 40% for action compliance
    communication: float = 0.30  # 30% for communication

    def normalize(self) -> "EvaluationWeights":
        """Normalize weights to sum to 1.0."""
        total = self.pose + self.action + self.communication
        if abs(total - 1.0) > 0.01:
            return EvaluationWeights(
                pose=self.pose / total,
                action=self.action / total,
                communication=self.communication / total,
            )
        return self

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "pose": self.pose,
            "action": self.action,
            "communication": self.communication,
        }


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""

    dimension: str
    score: float
    weight: float
    weighted_score: float
    grade: str
    feedback: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Complete evaluation result combining all dimensions."""

    # Session info
    session_id: str
    scenario_id: str
    scenario_name: str
    evaluation_time: float

    # Overall scores
    total_score: float  # 0-100
    grade: str  # A/B/C/D/F

    # Dimension scores
    pose_score: Optional[PoseScoreResult] = None
    action_score: Optional[ActionScoreResult] = None
    communication_score: Optional[CommunicationScoreResult] = None

    dimension_scores: Dict[str, DimensionScore] = field(default_factory=dict)

    # Weights used
    weights: Optional[EvaluationWeights] = None

    # Combined feedback
    strengths: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)

    # Summary
    summary: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "evaluation_time": self.evaluation_time,
            "total_score": self.total_score,
            "grade": self.grade,
            "weights": self.weights.to_dict() if self.weights else None,
            "dimension_scores": {
                name: {
                    "score": ds.score,
                    "weight": ds.weight,
                    "weighted_score": ds.weighted_score,
                    "grade": ds.grade,
                    "feedback": ds.feedback,
                }
                for name, ds in self.dimension_scores.items()
            },
            "pose_score": self.pose_score.to_dict() if self.pose_score else None,
            "action_score": self.action_score.to_dict() if self.action_score else None,
            "communication_score": (
                self.communication_score.to_dict()
                if self.communication_score
                else None
            ),
            "strengths": self.strengths,
            "improvements": self.improvements,
            "summary": self.summary,
        }


class Evaluator:
    """
    Main evaluation engine combining all scoring dimensions.

    Evaluates trainee performance across three dimensions:
    - Pose: Body posture and positioning (30% default)
    - Action: SOP action sequence compliance (40% default)
    - Communication: Speech timeliness and terminology (30% default)

    Usage:
        evaluator = Evaluator()

        # Full evaluation
        result = evaluator.evaluate(
            session_id="session_001",
            scenario_id="brace_position",
            pose_data=pose_analysis_result,
            sop_result=sop_analysis_result,
            comm_result=communication_result,
        )

        print(f"Total Score: {result.total_score}")
        print(f"Grade: {result.grade}")

        # Custom weights
        evaluator.set_weights(pose=0.4, action=0.3, communication=0.3)
    """

    # Grade thresholds
    GRADE_THRESHOLDS = [
        (90, "A", "优秀"),
        (80, "B", "良好"),
        (70, "C", "合格"),
        (60, "D", "待改进"),
        (0, "F", "不合格"),
    ]

    def __init__(
        self,
        weights: Optional[EvaluationWeights] = None,
    ) -> None:
        """
        Initialize evaluator.

        Args:
            weights: Optional custom dimension weights
        """
        self._weights = (weights or EvaluationWeights()).normalize()
        self._pose_scorer = PoseScorer()
        self._action_scorer = ActionScorer()
        self._communication_scorer = CommunicationScorer()

    def set_weights(
        self,
        pose: float = 0.30,
        action: float = 0.40,
        communication: float = 0.30,
    ) -> None:
        """Set dimension weights."""
        self._weights = EvaluationWeights(
            pose=pose,
            action=action,
            communication=communication,
        ).normalize()

    def evaluate(
        self,
        session_id: str,
        scenario_id: str,
        scenario_name: str = "",
        pose_data: Optional[Any] = None,
        pose_history: Optional[List[Any]] = None,
        sop_result: Optional[Any] = None,
        comm_result: Optional[Any] = None,
        brace_result: Optional[Any] = None,
    ) -> EvaluationResult:
        """
        Perform full evaluation across all dimensions.

        Args:
            session_id: Training session identifier
            scenario_id: Scenario being evaluated
            scenario_name: Human-readable scenario name
            pose_data: Single pose analysis result
            pose_history: List of pose data for stability analysis
            sop_result: SOP analysis result
            comm_result: Communication analysis result
            brace_result: Optional brace position result

        Returns:
            EvaluationResult with comprehensive scoring
        """
        eval_time = time.time()

        # Set scenario for scorers
        self._pose_scorer.set_scenario(scenario_id)

        # Score each dimension
        pose_score = self._evaluate_pose(
            pose_data, pose_history, brace_result, scenario_id
        )
        action_score = self._evaluate_action(sop_result)
        comm_score = self._evaluate_communication(comm_result, scenario_id)

        # Build dimension scores
        dimension_scores = {}

        if pose_score:
            dimension_scores["pose"] = DimensionScore(
                dimension="pose",
                score=pose_score.total_score,
                weight=self._weights.pose,
                weighted_score=pose_score.total_score * self._weights.pose,
                grade=pose_score.grade,
                feedback=pose_score.improvements,
            )

        if action_score:
            dimension_scores["action"] = DimensionScore(
                dimension="action",
                score=action_score.total_score,
                weight=self._weights.action,
                weighted_score=action_score.total_score * self._weights.action,
                grade=action_score.grade,
                feedback=action_score.improvements,
            )

        if comm_score:
            dimension_scores["communication"] = DimensionScore(
                dimension="communication",
                score=comm_score.total_score,
                weight=self._weights.communication,
                weighted_score=comm_score.total_score * self._weights.communication,
                grade=comm_score.grade,
                feedback=comm_score.improvements,
            )

        # Calculate total score
        total_score = self._calculate_total_score(
            pose_score, action_score, comm_score
        )

        # Determine grade
        grade = self._calculate_grade(total_score)

        # Combine feedback
        strengths, improvements = self._combine_feedback(
            pose_score, action_score, comm_score
        )

        # Generate summary
        summary = self._generate_summary(
            total_score, grade, dimension_scores, scenario_name or scenario_id
        )

        return EvaluationResult(
            session_id=session_id,
            scenario_id=scenario_id,
            scenario_name=scenario_name or scenario_id,
            evaluation_time=eval_time,
            total_score=total_score,
            grade=grade,
            pose_score=pose_score,
            action_score=action_score,
            communication_score=comm_score,
            dimension_scores=dimension_scores,
            weights=self._weights,
            strengths=strengths,
            improvements=improvements,
            summary=summary,
        )

    def evaluate_pose_only(
        self,
        pose_data: Any,
        brace_result: Optional[Any] = None,
        scenario: str = "brace_position",
    ) -> PoseScoreResult:
        """Evaluate only pose dimension."""
        self._pose_scorer.set_scenario(scenario)
        return self._pose_scorer.score(pose_data, brace_result)

    def evaluate_action_only(
        self,
        sop_result: Any,
    ) -> ActionScoreResult:
        """Evaluate only action dimension."""
        return self._action_scorer.score(sop_result)

    def evaluate_communication_only(
        self,
        comm_result: Any,
        scenario: Optional[str] = None,
    ) -> CommunicationScoreResult:
        """Evaluate only communication dimension."""
        return self._communication_scorer.score(comm_result, scenario)

    def _evaluate_pose(
        self,
        pose_data: Optional[Any],
        pose_history: Optional[List[Any]],
        brace_result: Optional[Any],
        scenario: str,
    ) -> Optional[PoseScoreResult]:
        """Evaluate pose dimension."""
        if pose_history and len(pose_history) > 1:
            return self._pose_scorer.score_with_history(pose_history)
        elif pose_data:
            return self._pose_scorer.score(pose_data, brace_result)
        return None

    def _evaluate_action(
        self,
        sop_result: Optional[Any],
    ) -> Optional[ActionScoreResult]:
        """Evaluate action dimension."""
        if sop_result:
            return self._action_scorer.score(sop_result)
        return None

    def _evaluate_communication(
        self,
        comm_result: Optional[Any],
        scenario: Optional[str],
    ) -> Optional[CommunicationScoreResult]:
        """Evaluate communication dimension."""
        if comm_result:
            return self._communication_scorer.score(comm_result, scenario)
        return None

    def _calculate_total_score(
        self,
        pose_score: Optional[PoseScoreResult],
        action_score: Optional[ActionScoreResult],
        comm_score: Optional[CommunicationScoreResult],
    ) -> float:
        """Calculate weighted total score."""
        total = 0.0
        total_weight = 0.0

        if pose_score:
            total += pose_score.total_score * self._weights.pose
            total_weight += self._weights.pose

        if action_score:
            total += action_score.total_score * self._weights.action
            total_weight += self._weights.action

        if comm_score:
            total += comm_score.total_score * self._weights.communication
            total_weight += self._weights.communication

        if total_weight > 0:
            # Normalize by actual weights used
            return total / total_weight * (
                self._weights.pose
                + self._weights.action
                + self._weights.communication
            )
        return 0.0

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        for threshold, grade, _ in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"

    def _get_grade_description(self, grade: str) -> str:
        """Get description for a grade."""
        for _, g, desc in self.GRADE_THRESHOLDS:
            if g == grade:
                return desc
        return "不合格"

    def _combine_feedback(
        self,
        pose_score: Optional[PoseScoreResult],
        action_score: Optional[ActionScoreResult],
        comm_score: Optional[CommunicationScoreResult],
    ) -> tuple:
        """Combine feedback from all dimensions."""
        strengths = []
        improvements = []

        if pose_score:
            strengths.extend(pose_score.strengths[:2])
            improvements.extend(pose_score.improvements[:2])

        if action_score:
            strengths.extend(action_score.strengths[:2])
            improvements.extend(action_score.improvements[:2])

        if comm_score:
            strengths.extend(comm_score.strengths[:2])
            improvements.extend(comm_score.improvements[:2])

        return strengths, improvements

    def _generate_summary(
        self,
        total_score: float,
        grade: str,
        dimension_scores: Dict[str, DimensionScore],
        scenario_name: str,
    ) -> str:
        """Generate evaluation summary."""
        grade_desc = self._get_grade_description(grade)

        summary_parts = [
            f"场景「{scenario_name}」评估结果：{grade_desc}（{grade}级，{total_score:.1f}分）",
        ]

        dimension_names = {
            "pose": "姿态标准",
            "action": "动作时效",
            "communication": "沟通协同",
        }

        for dim, ds in dimension_scores.items():
            name = dimension_names.get(dim, dim)
            summary_parts.append(f"{name}: {ds.score:.1f}分 ({ds.grade})")

        return "。".join(summary_parts) + "。"

    @property
    def weights(self) -> EvaluationWeights:
        """Get current weights."""
        return self._weights

    @property
    def pose_scorer(self) -> PoseScorer:
        """Get pose scorer for customization."""
        return self._pose_scorer

    @property
    def action_scorer(self) -> ActionScorer:
        """Get action scorer for customization."""
        return self._action_scorer

    @property
    def communication_scorer(self) -> CommunicationScorer:
        """Get communication scorer for customization."""
        return self._communication_scorer
