"""
Communication Scorer - Evaluates speech and communication quality.

Analyzes communication data to calculate:
- Response timeliness
- Terminology correctness
- Speech clarity
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class CommunicationAspect(Enum):
    """Aspects of communication evaluation."""

    TIMELINESS = "timeliness"  # Response speed
    TERMINOLOGY = "terminology"  # Correct term usage
    CLARITY = "clarity"  # Speech clarity
    COMPLETENESS = "completeness"  # Information completeness


@dataclass
class AspectScore:
    """Score for a communication aspect."""

    aspect: CommunicationAspect
    score: float  # 0-100
    weight: float
    weighted_score: float
    details: List[str] = field(default_factory=list)
    feedback: str = ""


@dataclass
class CommunicationScoreResult:
    """Complete communication scoring result."""

    # Overall score
    total_score: float  # 0-100
    grade: str  # A/B/C/D/F

    # Aspect scores
    aspect_scores: Dict[CommunicationAspect, AspectScore] = field(
        default_factory=dict
    )

    # Metrics
    response_time: Optional[float] = None
    terminology_accuracy: float = 0.0
    clarity_score: float = 0.0

    # Terms used
    correct_terms: List[str] = field(default_factory=list)
    missed_terms: List[str] = field(default_factory=list)

    # Feedback
    strengths: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "total_score": self.total_score,
            "grade": self.grade,
            "aspect_scores": {
                aspect.value: {
                    "score": as_.score,
                    "weight": as_.weight,
                    "weighted_score": as_.weighted_score,
                    "feedback": as_.feedback,
                }
                for aspect, as_ in self.aspect_scores.items()
            },
            "response_time": self.response_time,
            "terminology_accuracy": self.terminology_accuracy,
            "clarity_score": self.clarity_score,
            "correct_terms": self.correct_terms,
            "missed_terms": self.missed_terms,
            "strengths": self.strengths,
            "improvements": self.improvements,
        }


class CommunicationScorer:
    """
    Communication scoring engine for speech evaluation.

    Evaluates communication quality based on timeliness,
    terminology usage, and clarity.

    Usage:
        scorer = CommunicationScorer()

        # Score from communication analysis
        result = scorer.score(comm_analysis_result)
        print(f"Score: {result.total_score}, Grade: {result.grade}")

        # Or score with expected terms
        result = scorer.score_with_expectations(
            comm_result,
            expected_terms=["请系好安全带", "保持镇静"],
            time_limit=5.0,
        )
    """

    # Grade thresholds
    GRADE_THRESHOLDS = [
        (90, "A"),
        (80, "B"),
        (70, "C"),
        (60, "D"),
        (0, "F"),
    ]

    # Default aspect weights
    DEFAULT_WEIGHTS = {
        CommunicationAspect.TIMELINESS: 0.30,
        CommunicationAspect.TERMINOLOGY: 0.35,
        CommunicationAspect.CLARITY: 0.20,
        CommunicationAspect.COMPLETENESS: 0.15,
    }

    # Scenario-specific expected terms
    SCENARIO_TERMS = {
        "brace_position": [
            "防冲击姿势",
            "低头弯腰",
            "双手抱头",
            "保持姿势",
        ],
        "fire_emergency": [
            "发现火情",
            "乘务长",
            "灭火器",
            "请保持冷静",
        ],
        "evacuation": [
            "紧急撤离",
            "解开安全带",
            "不要携带行李",
            "向最近出口移动",
        ],
        "medical_emergency": [
            "医疗紧急情况",
            "请问有医生吗",
            "急救箱",
            "保持通畅",
        ],
    }

    def __init__(
        self,
        weights: Optional[Dict[CommunicationAspect, float]] = None,
        response_time_limit: float = 5.0,
    ) -> None:
        """
        Initialize communication scorer.

        Args:
            weights: Optional custom aspect weights
            response_time_limit: Maximum acceptable response time
        """
        self._weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._response_time_limit = response_time_limit

    def set_weights(self, weights: Dict[CommunicationAspect, float]) -> None:
        """Set aspect weights."""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            self._weights = {k: v / total for k, v in weights.items()}
        else:
            self._weights = weights.copy()

    def set_response_time_limit(self, limit: float) -> None:
        """Set response time limit."""
        self._response_time_limit = limit

    def score(
        self,
        comm_result: Any,
        scenario: Optional[str] = None,
    ) -> CommunicationScoreResult:
        """
        Score from a CommunicationAnalysisResult.

        Args:
            comm_result: CommunicationAnalysisResult
            scenario: Optional scenario for expected terms

        Returns:
            CommunicationScoreResult with detailed scoring
        """
        expected_terms = self.SCENARIO_TERMS.get(scenario, []) if scenario else []

        return self.score_with_expectations(
            comm_result,
            expected_terms=expected_terms,
            time_limit=self._response_time_limit,
        )

    def score_with_expectations(
        self,
        comm_result: Any,
        expected_terms: Optional[List[str]] = None,
        time_limit: Optional[float] = None,
    ) -> CommunicationScoreResult:
        """
        Score with specific expectations.

        Args:
            comm_result: CommunicationAnalysisResult or dict
            expected_terms: Expected terminology
            time_limit: Response time limit

        Returns:
            CommunicationScoreResult
        """
        expected = expected_terms or []
        limit = time_limit or self._response_time_limit

        aspect_scores = {}

        # Score timeliness
        timeliness_score = self._score_timeliness(comm_result, limit)
        aspect_scores[CommunicationAspect.TIMELINESS] = timeliness_score

        # Score terminology
        terminology_score, correct_terms, missed_terms = self._score_terminology(
            comm_result, expected
        )
        aspect_scores[CommunicationAspect.TERMINOLOGY] = terminology_score

        # Score clarity
        clarity_score = self._score_clarity(comm_result)
        aspect_scores[CommunicationAspect.CLARITY] = clarity_score

        # Score completeness
        completeness_score = self._score_completeness(comm_result, expected)
        aspect_scores[CommunicationAspect.COMPLETENESS] = completeness_score

        # Calculate total score
        total_score = sum(as_.weighted_score for as_ in aspect_scores.values())

        # Generate feedback
        strengths, improvements = self._generate_feedback(
            aspect_scores, correct_terms, missed_terms
        )

        # Extract metrics
        response_time = self._get_response_time(comm_result)
        terminology_accuracy = (
            len(correct_terms) / len(expected) * 100 if expected else 100.0
        )
        clarity = clarity_score.score

        return CommunicationScoreResult(
            total_score=total_score,
            grade=self._calculate_grade(total_score),
            aspect_scores=aspect_scores,
            response_time=response_time,
            terminology_accuracy=terminology_accuracy,
            clarity_score=clarity,
            correct_terms=correct_terms,
            missed_terms=missed_terms,
            strengths=strengths,
            improvements=improvements,
        )

    def _score_timeliness(
        self,
        comm_result: Any,
        time_limit: float,
    ) -> AspectScore:
        """Score response timeliness."""
        weight = self._weights[CommunicationAspect.TIMELINESS]

        response_time = self._get_response_time(comm_result)
        if response_time is None:
            # No timing data
            score = 50.0
            feedback = "无响应时间数据"
        elif response_time <= time_limit * 0.5:
            score = 100.0
            feedback = f"响应迅速 ({response_time:.1f}秒)"
        elif response_time <= time_limit:
            ratio = (response_time - time_limit * 0.5) / (time_limit * 0.5)
            score = 100.0 - ratio * 20.0
            feedback = f"响应及时 ({response_time:.1f}秒)"
        elif response_time <= time_limit * 2:
            ratio = (response_time - time_limit) / time_limit
            score = 80.0 - ratio * 40.0
            feedback = f"响应略慢 ({response_time:.1f}秒)"
        else:
            score = max(0.0, 40.0 - (response_time - time_limit * 2) * 10)
            feedback = f"响应延迟 ({response_time:.1f}秒)"

        return AspectScore(
            aspect=CommunicationAspect.TIMELINESS,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            feedback=feedback,
        )

    def _score_terminology(
        self,
        comm_result: Any,
        expected_terms: List[str],
    ) -> tuple:
        """Score terminology usage."""
        weight = self._weights[CommunicationAspect.TERMINOLOGY]

        # Get detected terms
        detected_terms = self._get_detected_terms(comm_result)
        text = self._get_text(comm_result)

        correct_terms = []
        missed_terms = []

        for term in expected_terms:
            if term in detected_terms or term in text:
                correct_terms.append(term)
            else:
                missed_terms.append(term)

        if not expected_terms:
            score = 100.0
            feedback = "无特定术语要求"
        else:
            accuracy = len(correct_terms) / len(expected_terms)
            score = accuracy * 100
            if accuracy >= 1.0:
                feedback = "术语使用完全正确"
            elif accuracy >= 0.7:
                feedback = f"术语使用较好 ({len(correct_terms)}/{len(expected_terms)})"
            elif accuracy >= 0.5:
                feedback = f"术语使用一般 ({len(correct_terms)}/{len(expected_terms)})"
            else:
                feedback = f"术语使用不足 ({len(correct_terms)}/{len(expected_terms)})"

        aspect_score = AspectScore(
            aspect=CommunicationAspect.TERMINOLOGY,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            details=correct_terms,
            feedback=feedback,
        )

        return aspect_score, correct_terms, missed_terms

    def _score_clarity(self, comm_result: Any) -> AspectScore:
        """Score speech clarity."""
        weight = self._weights[CommunicationAspect.CLARITY]

        # Get clarity from result
        if hasattr(comm_result, "clarity_score"):
            clarity = comm_result.clarity_score
        elif isinstance(comm_result, dict) and "clarity_score" in comm_result:
            clarity = comm_result["clarity_score"]
        else:
            # Estimate from confidence
            confidence = self._get_confidence(comm_result)
            clarity = confidence * 100 if confidence else 80.0

        score = clarity

        if score >= 90:
            feedback = "语音清晰度优秀"
        elif score >= 75:
            feedback = "语音清晰度良好"
        elif score >= 60:
            feedback = "语音清晰度一般"
        else:
            feedback = "语音清晰度较差"

        return AspectScore(
            aspect=CommunicationAspect.CLARITY,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            feedback=feedback,
        )

    def _score_completeness(
        self,
        comm_result: Any,
        expected_terms: List[str],
    ) -> AspectScore:
        """Score information completeness."""
        weight = self._weights[CommunicationAspect.COMPLETENESS]

        text = self._get_text(comm_result)
        text_length = len(text) if text else 0

        # Score based on content presence
        if not expected_terms:
            # No expectations, score based on content presence
            if text_length > 50:
                score = 100.0
                feedback = "通讯内容完整"
            elif text_length > 20:
                score = 80.0
                feedback = "通讯内容较完整"
            elif text_length > 0:
                score = 60.0
                feedback = "通讯内容简短"
            else:
                score = 0.0
                feedback = "无通讯内容"
        else:
            # Check how many expected items are mentioned
            mentioned = 0
            for term in expected_terms:
                if term in text:
                    mentioned += 1

            ratio = mentioned / len(expected_terms)
            score = ratio * 100

            if ratio >= 0.9:
                feedback = "信息完整"
            elif ratio >= 0.7:
                feedback = "信息较完整"
            elif ratio >= 0.5:
                feedback = "信息部分完整"
            else:
                feedback = "信息不完整"

        return AspectScore(
            aspect=CommunicationAspect.COMPLETENESS,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            feedback=feedback,
        )

    def _get_response_time(self, comm_result: Any) -> Optional[float]:
        """Extract response time from result."""
        if hasattr(comm_result, "response_timing"):
            timing = comm_result.response_timing
            if timing and hasattr(timing, "response_time"):
                return timing.response_time
        if hasattr(comm_result, "first_response_time"):
            return comm_result.first_response_time
        if isinstance(comm_result, dict):
            return comm_result.get("response_time") or comm_result.get(
                "first_response_time"
            )
        return None

    def _get_detected_terms(self, comm_result: Any) -> List[str]:
        """Extract detected terms from result."""
        if hasattr(comm_result, "terminology_matches"):
            matches = comm_result.terminology_matches
            return [m.term if hasattr(m, "term") else str(m) for m in matches]
        if isinstance(comm_result, dict) and "terminology_matches" in comm_result:
            return [
                m.get("term", str(m)) if isinstance(m, dict) else str(m)
                for m in comm_result["terminology_matches"]
            ]
        return []

    def _get_text(self, comm_result: Any) -> str:
        """Extract text from result."""
        if hasattr(comm_result, "text"):
            return comm_result.text or ""
        if isinstance(comm_result, dict):
            return comm_result.get("text", "")
        return ""

    def _get_confidence(self, comm_result: Any) -> Optional[float]:
        """Extract confidence from result."""
        if hasattr(comm_result, "confidence"):
            return comm_result.confidence
        if isinstance(comm_result, dict):
            return comm_result.get("confidence")
        return None

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"

    def _generate_feedback(
        self,
        aspect_scores: Dict[CommunicationAspect, AspectScore],
        correct_terms: List[str],
        missed_terms: List[str],
    ) -> tuple:
        """Generate overall feedback."""
        strengths = []
        improvements = []

        for aspect, as_ in aspect_scores.items():
            if as_.score >= 90:
                strengths.append(as_.feedback)
            elif as_.score < 70:
                improvements.append(as_.feedback)

        if correct_terms:
            strengths.append(f"正确使用术语: {', '.join(correct_terms[:3])}")

        if missed_terms:
            improvements.append(f"建议使用术语: {', '.join(missed_terms[:3])}")

        return strengths, improvements

    def get_scenario_terms(self, scenario: str) -> List[str]:
        """Get expected terms for a scenario."""
        return self.SCENARIO_TERMS.get(scenario, [])

    def add_scenario_terms(self, scenario: str, terms: List[str]) -> None:
        """Add expected terms for a scenario."""
        if scenario in self.SCENARIO_TERMS:
            self.SCENARIO_TERMS[scenario].extend(terms)
        else:
            self.SCENARIO_TERMS[scenario] = terms
