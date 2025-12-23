"""
Action Scorer - Evaluates SOP action sequence compliance.

Analyzes action timing and sequence against SOP rules to calculate:
- Time compliance scores
- Sequence correctness
- Overall action efficiency
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class ActionCompliance(Enum):
    """Action compliance status."""

    ON_TIME = "on_time"
    DELAYED = "delayed"
    EARLY = "early"
    MISSING = "missing"
    EXTRA = "extra"


@dataclass
class ActionScore:
    """Score for a single action."""

    action_id: str
    action_name: str
    compliance: ActionCompliance
    time_limit: float
    actual_time: Optional[float]
    time_deviation: float  # Positive = late, negative = early
    score: float  # 0-100
    feedback: str = ""


@dataclass
class ActionScoreResult:
    """Complete action scoring result."""

    # Overall score
    total_score: float  # 0-100
    grade: str  # A/B/C/D/F

    # Scenario info
    scenario_id: str
    scenario_name: str

    # Action scores
    action_scores: List[ActionScore] = field(default_factory=list)

    # Metrics
    completion_rate: float = 0.0  # Percentage of completed actions
    average_delay: float = 0.0  # Average delay in seconds
    sequence_correct: bool = True

    # Feedback
    strengths: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "total_score": self.total_score,
            "grade": self.grade,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "action_scores": [
                {
                    "action_id": a.action_id,
                    "action_name": a.action_name,
                    "compliance": a.compliance.value,
                    "time_limit": a.time_limit,
                    "actual_time": a.actual_time,
                    "time_deviation": a.time_deviation,
                    "score": a.score,
                    "feedback": a.feedback,
                }
                for a in self.action_scores
            ],
            "completion_rate": self.completion_rate,
            "average_delay": self.average_delay,
            "sequence_correct": self.sequence_correct,
            "strengths": self.strengths,
            "improvements": self.improvements,
        }


class ActionScorer:
    """
    Action scoring engine for SOP compliance evaluation.

    Evaluates action sequences against SOP rules and generates
    scores based on timing and sequence correctness.

    Usage:
        scorer = ActionScorer()

        # Score from SOP analysis result
        result = scorer.score(sop_analysis_result)
        print(f"Score: {result.total_score}, Grade: {result.grade}")

        # Or score individual actions
        scorer.set_scenario("fire_emergency", steps)
        scorer.record_action("ACT_001", timestamp=1.5)
        result = scorer.calculate_score()
    """

    # Grade thresholds
    GRADE_THRESHOLDS = [
        (90, "A"),
        (80, "B"),
        (70, "C"),
        (60, "D"),
        (0, "F"),
    ]

    # Scoring weights
    WEIGHT_TIMING = 0.6  # Weight for timing compliance
    WEIGHT_COMPLETION = 0.3  # Weight for completion rate
    WEIGHT_SEQUENCE = 0.1  # Weight for sequence correctness

    def __init__(self) -> None:
        """Initialize action scorer."""
        self._scenario_id: Optional[str] = None
        self._scenario_name: str = ""
        self._steps: List[Dict] = []
        self._trigger_time: Optional[float] = None
        self._recorded_actions: Dict[str, float] = {}

    def score(self, sop_result: Any) -> ActionScoreResult:
        """
        Score from an SOPAnalysisResult.

        Args:
            sop_result: SOPAnalysisResult from SOPAnalyzer

        Returns:
            ActionScoreResult with detailed scoring
        """
        if sop_result is None:
            return ActionScoreResult(
                total_score=0.0,
                grade="F",
                scenario_id="",
                scenario_name="",
                improvements=["无SOP分析结果"],
            )

        action_scores = []
        total_score_sum = 0.0
        completed_count = 0
        total_delay = 0.0
        sequence_correct = True

        steps_compliance = getattr(sop_result, "steps_compliance", [])

        for sc in steps_compliance:
            step = sc.step
            status = sc.status

            # Determine compliance
            if status.value == "compliant":
                compliance = ActionCompliance.ON_TIME
                time_dev = 0.0
                score = 100.0
                completed_count += 1
            elif status.value == "timeout":
                compliance = ActionCompliance.DELAYED
                time_dev = sc.deviation or 0.0
                score = self._calculate_time_score(time_dev, step.time_limit)
                total_delay += time_dev
                completed_count += 1
            elif status.value == "pending":
                compliance = ActionCompliance.MISSING
                time_dev = step.time_limit  # Maximum deviation
                score = 0.0
                sequence_correct = False
            else:
                compliance = ActionCompliance.MISSING
                time_dev = 0.0
                score = 50.0  # Partial credit for optional

            feedback = self._generate_action_feedback(
                step.action_name, compliance, time_dev, step.time_limit
            )

            action_scores.append(
                ActionScore(
                    action_id=step.action_id,
                    action_name=step.action_name,
                    compliance=compliance,
                    time_limit=step.time_limit,
                    actual_time=sc.actual_time,
                    time_deviation=time_dev,
                    score=score,
                    feedback=feedback,
                )
            )

            total_score_sum += score

        # Calculate metrics
        total_actions = len(steps_compliance) if steps_compliance else 1
        avg_action_score = total_score_sum / total_actions if total_actions > 0 else 0
        completion_rate = completed_count / total_actions if total_actions > 0 else 0
        avg_delay = total_delay / completed_count if completed_count > 0 else 0

        # Calculate total score with weights
        timing_score = avg_action_score
        completion_score = completion_rate * 100
        sequence_score = 100 if sequence_correct else 50

        total_score = (
            timing_score * self.WEIGHT_TIMING
            + completion_score * self.WEIGHT_COMPLETION
            + sequence_score * self.WEIGHT_SEQUENCE
        )

        # Check total time compliance
        if hasattr(sop_result, "total_time") and hasattr(sop_result, "time_limit"):
            if sop_result.total_time > sop_result.time_limit:
                # Penalty for exceeding total time
                over_ratio = sop_result.total_time / sop_result.time_limit
                total_score *= max(0.5, 1.0 - (over_ratio - 1.0) * 0.3)

        # Generate feedback
        strengths, improvements = self._generate_feedback(
            action_scores, completion_rate, sequence_correct, sop_result
        )

        return ActionScoreResult(
            total_score=total_score,
            grade=self._calculate_grade(total_score),
            scenario_id=getattr(sop_result, "scenario_id", ""),
            scenario_name=getattr(sop_result, "scenario_name", ""),
            action_scores=action_scores,
            completion_rate=completion_rate,
            average_delay=avg_delay,
            sequence_correct=sequence_correct,
            strengths=strengths,
            improvements=improvements,
        )

    def set_scenario(
        self,
        scenario_id: str,
        scenario_name: str,
        steps: List[Dict],
        trigger_time: float,
    ) -> None:
        """
        Set up scenario for manual scoring.

        Args:
            scenario_id: Scenario identifier
            scenario_name: Human-readable name
            steps: List of step definitions
            trigger_time: When the scenario was triggered
        """
        self._scenario_id = scenario_id
        self._scenario_name = scenario_name
        self._steps = steps
        self._trigger_time = trigger_time
        self._recorded_actions.clear()

    def record_action(
        self,
        action_id: str,
        timestamp: float,
    ) -> None:
        """Record an action completion."""
        if self._trigger_time is not None:
            relative_time = timestamp - self._trigger_time
            self._recorded_actions[action_id] = relative_time

    def calculate_score(self) -> ActionScoreResult:
        """Calculate score from recorded actions."""
        if not self._scenario_id or not self._steps:
            return ActionScoreResult(
                total_score=0.0,
                grade="F",
                scenario_id="",
                scenario_name="",
                improvements=["未设置场景"],
            )

        action_scores = []
        completed_count = 0
        total_delay = 0.0
        total_score_sum = 0.0

        for step in self._steps:
            action_id = step.get("action_id", step.get("action", ""))
            action_name = step.get("action_name", step.get("name", action_id))
            time_limit = step.get("time_limit", 10.0)

            actual_time = self._recorded_actions.get(action_id)

            if actual_time is not None:
                if actual_time <= time_limit:
                    compliance = ActionCompliance.ON_TIME
                    time_dev = 0.0
                    score = 100.0
                else:
                    compliance = ActionCompliance.DELAYED
                    time_dev = actual_time - time_limit
                    score = self._calculate_time_score(time_dev, time_limit)
                    total_delay += time_dev
                completed_count += 1
            else:
                compliance = ActionCompliance.MISSING
                time_dev = time_limit
                score = 0.0

            feedback = self._generate_action_feedback(
                action_name, compliance, time_dev, time_limit
            )

            action_scores.append(
                ActionScore(
                    action_id=action_id,
                    action_name=action_name,
                    compliance=compliance,
                    time_limit=time_limit,
                    actual_time=actual_time,
                    time_deviation=time_dev,
                    score=score,
                    feedback=feedback,
                )
            )

            total_score_sum += score

        total_actions = len(self._steps)
        avg_action_score = total_score_sum / total_actions if total_actions > 0 else 0
        completion_rate = completed_count / total_actions if total_actions > 0 else 0
        avg_delay = total_delay / completed_count if completed_count > 0 else 0

        total_score = (
            avg_action_score * self.WEIGHT_TIMING
            + completion_rate * 100 * self.WEIGHT_COMPLETION
            + (100 if completion_rate == 1.0 else 50) * self.WEIGHT_SEQUENCE
        )

        strengths, improvements = self._generate_feedback(
            action_scores, completion_rate, completion_rate == 1.0, None
        )

        return ActionScoreResult(
            total_score=total_score,
            grade=self._calculate_grade(total_score),
            scenario_id=self._scenario_id,
            scenario_name=self._scenario_name,
            action_scores=action_scores,
            completion_rate=completion_rate,
            average_delay=avg_delay,
            sequence_correct=completion_rate == 1.0,
            strengths=strengths,
            improvements=improvements,
        )

    def _calculate_time_score(
        self,
        deviation: float,
        time_limit: float,
    ) -> float:
        """Calculate score based on time deviation."""
        if deviation <= 0:
            return 100.0

        # Score decreases with deviation
        ratio = deviation / time_limit
        if ratio <= 0.5:
            return 100.0 - ratio * 40  # 80-100
        elif ratio <= 1.0:
            return 80.0 - (ratio - 0.5) * 60  # 50-80
        else:
            return max(0.0, 50.0 - (ratio - 1.0) * 50)  # 0-50

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"

    def _generate_action_feedback(
        self,
        action_name: str,
        compliance: ActionCompliance,
        deviation: float,
        time_limit: float,
    ) -> str:
        """Generate feedback for a single action."""
        if compliance == ActionCompliance.ON_TIME:
            return f"{action_name} 及时完成"
        elif compliance == ActionCompliance.DELAYED:
            return f"{action_name} 延迟 {deviation:.1f}秒"
        elif compliance == ActionCompliance.MISSING:
            return f"{action_name} 未完成"
        elif compliance == ActionCompliance.EARLY:
            return f"{action_name} 提前完成"
        else:
            return f"{action_name} 额外动作"

    def _generate_feedback(
        self,
        action_scores: List[ActionScore],
        completion_rate: float,
        sequence_correct: bool,
        sop_result: Optional[Any],
    ) -> tuple:
        """Generate overall feedback."""
        strengths = []
        improvements = []

        # Count on-time actions
        on_time_count = sum(
            1 for a in action_scores if a.compliance == ActionCompliance.ON_TIME
        )
        delayed_count = sum(
            1 for a in action_scores if a.compliance == ActionCompliance.DELAYED
        )
        missing_count = sum(
            1 for a in action_scores if a.compliance == ActionCompliance.MISSING
        )

        if on_time_count == len(action_scores):
            strengths.append("所有动作均及时完成")
        elif on_time_count > 0:
            strengths.append(f"{on_time_count}个动作及时完成")

        if completion_rate == 1.0:
            strengths.append("所有必需动作已完成")

        if delayed_count > 0:
            avg_delay = sum(
                a.time_deviation
                for a in action_scores
                if a.compliance == ActionCompliance.DELAYED
            ) / delayed_count
            improvements.append(f"{delayed_count}个动作延迟，平均延迟{avg_delay:.1f}秒")

        if missing_count > 0:
            missing_names = [
                a.action_name
                for a in action_scores
                if a.compliance == ActionCompliance.MISSING
            ]
            improvements.append(f"缺少动作: {', '.join(missing_names)}")

        if sop_result and hasattr(sop_result, "total_time"):
            if hasattr(sop_result, "time_limit"):
                if sop_result.total_time <= sop_result.time_limit:
                    strengths.append(
                        f"总用时{sop_result.total_time:.1f}秒，在规定时间内"
                    )
                else:
                    over = sop_result.total_time - sop_result.time_limit
                    improvements.append(f"总用时超过限制{over:.1f}秒")

        return strengths, improvements

    def reset(self) -> None:
        """Reset scorer state."""
        self._scenario_id = None
        self._scenario_name = ""
        self._steps.clear()
        self._trigger_time = None
        self._recorded_actions.clear()
