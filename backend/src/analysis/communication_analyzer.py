"""
Communication Analyzer - Analyzes cabin crew verbal communications.

Monitors speech for:
- Standard terminology usage
- Response timeliness
- Command acknowledgment
- Communication clarity
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from src.perception.asr_engine import ASRResult, ASRSegment, STANDARD_TERMINOLOGY


class TerminologyCategory(Enum):
    """Categories of standard terminology."""

    EMERGENCY = "emergency"
    SAFETY = "safety"
    COMMUNICATION = "communication"
    COORDINATION = "coordination"


class ResponseType(Enum):
    """Types of communication responses."""

    COMMAND = "command"  # Crew member giving command
    ACKNOWLEDGMENT = "acknowledgment"  # Confirming received command
    REPORT = "report"  # Status report
    REQUEST = "request"  # Asking for something


@dataclass
class TerminologyMatch:
    """A match of standard terminology in speech."""

    term_id: str  # Standard term identifier
    matched_text: str  # Actual text that matched
    category: TerminologyCategory
    start_time: float
    end_time: float
    confidence: float
    is_correct: bool  # Whether usage was correct


@dataclass
class ResponseTiming:
    """Timing analysis of a response."""

    trigger_text: str  # What triggered the response
    trigger_time: float
    response_text: str
    response_time: float
    delay: float  # Time between trigger and response
    is_timely: bool  # Within acceptable time limit
    time_limit: float  # Expected time limit


@dataclass
class CommunicationEvent:
    """A single communication event."""

    text: str
    response_type: ResponseType
    start_time: float
    end_time: float
    terminology_matches: List[TerminologyMatch] = field(default_factory=list)
    is_clear: bool = True  # Whether communication was clear
    feedback: str = ""


@dataclass
class CommunicationAnalysisResult:
    """Complete communication analysis result."""

    # Input data
    asr_result: ASRResult

    # Analysis results
    events: List[CommunicationEvent] = field(default_factory=list)
    terminology_matches: List[TerminologyMatch] = field(default_factory=list)
    response_timings: List[ResponseTiming] = field(default_factory=list)

    # Scores
    terminology_score: float = 0.0  # Correct terminology usage (0-100)
    timeliness_score: float = 0.0  # Response timeliness (0-100)
    clarity_score: float = 0.0  # Communication clarity (0-100)
    overall_score: float = 0.0  # Combined score (0-100)

    # Summary
    total_commands: int = 0
    acknowledged_commands: int = 0
    missed_terminology: List[str] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "terminology_score": self.terminology_score,
            "timeliness_score": self.timeliness_score,
            "clarity_score": self.clarity_score,
            "overall_score": self.overall_score,
            "total_commands": self.total_commands,
            "acknowledged_commands": self.acknowledged_commands,
            "events": [
                {
                    "text": e.text,
                    "type": e.response_type.value,
                    "start_time": e.start_time,
                    "end_time": e.end_time,
                }
                for e in self.events
            ],
            "terminology_matches": [
                {
                    "term_id": m.term_id,
                    "matched_text": m.matched_text,
                    "category": m.category.value,
                    "is_correct": m.is_correct,
                }
                for m in self.terminology_matches
            ],
            "missed_terminology": self.missed_terminology,
            "feedback": self.feedback,
        }


class CommunicationAnalyzer:
    """
    Analyzes cabin crew verbal communications.

    Evaluates:
    - Use of standard aviation terminology
    - Response timeliness to commands
    - Command acknowledgment patterns
    - Communication clarity

    Usage:
        analyzer = CommunicationAnalyzer()

        # Analyze ASR result
        result = analyzer.analyze(asr_result)

        print(f"Terminology Score: {result.terminology_score}")
        print(f"Timeliness Score: {result.timeliness_score}")
        print(f"Overall Score: {result.overall_score}")

        for match in result.terminology_matches:
            print(f"  Found: {match.term_id} at {match.start_time:.2f}s")
    """

    # Default timing limits (seconds)
    DEFAULT_TIME_LIMITS = {
        "acknowledgment": 2.0,  # Acknowledge within 2 seconds
        "emergency_response": 3.0,  # Respond to emergency within 3 seconds
        "report": 5.0,  # Complete report within 5 seconds
    }

    # Terminology mappings
    TERMINOLOGY_CATEGORIES = {
        "brace": TerminologyCategory.EMERGENCY,
        "evacuate": TerminologyCategory.EMERGENCY,
        "fire": TerminologyCategory.EMERGENCY,
        "check_seatbelt": TerminologyCategory.SAFETY,
        "check_tray": TerminologyCategory.SAFETY,
        "check_seat": TerminologyCategory.SAFETY,
        "confirm": TerminologyCategory.COMMUNICATION,
        "report": TerminologyCategory.COMMUNICATION,
        "standby": TerminologyCategory.COMMUNICATION,
        "ready": TerminologyCategory.COORDINATION,
        "clear": TerminologyCategory.COORDINATION,
        "assist": TerminologyCategory.COORDINATION,
    }

    def __init__(
        self,
        terminology: Optional[Dict[str, List[str]]] = None,
        time_limits: Optional[Dict[str, float]] = None,
        min_confidence: float = 0.5,
    ) -> None:
        """
        Initialize communication analyzer.

        Args:
            terminology: Custom terminology dictionary
            time_limits: Custom time limits for responses
            min_confidence: Minimum confidence for matches
        """
        self._terminology = terminology or STANDARD_TERMINOLOGY.copy()
        self._time_limits = time_limits or self.DEFAULT_TIME_LIMITS.copy()
        self._min_confidence = min_confidence

        # Build regex patterns for terminology matching
        self._build_patterns()

        # Track command-response pairs
        self._pending_commands: List[Tuple[str, float, str]] = []

    def _build_patterns(self) -> None:
        """Build regex patterns for terminology matching."""
        self._patterns: Dict[str, re.Pattern] = {}

        for term_id, variations in self._terminology.items():
            # Create pattern that matches any variation
            escaped = [re.escape(v) for v in variations]
            pattern = "|".join(escaped)
            self._patterns[term_id] = re.compile(pattern, re.IGNORECASE)

    def analyze(
        self,
        asr_result: ASRResult,
        expected_terminology: Optional[Set[str]] = None,
    ) -> CommunicationAnalysisResult:
        """
        Analyze communication from ASR result.

        Args:
            asr_result: ASR transcription result
            expected_terminology: Set of expected term IDs

        Returns:
            CommunicationAnalysisResult with all analysis data
        """
        if not asr_result.success:
            return CommunicationAnalysisResult(
                asr_result=asr_result,
                feedback=["语音识别失败，无法进行通讯分析"],
            )

        # Analyze each segment
        events = []
        all_matches = []

        for segment in asr_result.segments:
            if segment.confidence < self._min_confidence:
                continue

            # Find terminology matches
            matches = self._find_terminology(segment)
            all_matches.extend(matches)

            # Classify response type
            response_type = self._classify_response(segment.text, matches)

            # Create event
            event = CommunicationEvent(
                text=segment.text,
                response_type=response_type,
                start_time=segment.start_time,
                end_time=segment.end_time,
                terminology_matches=matches,
                is_clear=segment.confidence > 0.7,
            )
            events.append(event)

        # Analyze response timings
        response_timings = self._analyze_timings(events)

        # Calculate scores
        terminology_score = self._calculate_terminology_score(
            all_matches, expected_terminology
        )
        timeliness_score = self._calculate_timeliness_score(response_timings)
        clarity_score = self._calculate_clarity_score(asr_result, events)

        # Overall score (weighted average)
        overall_score = (
            terminology_score * 0.4 +
            timeliness_score * 0.3 +
            clarity_score * 0.3
        )

        # Find missed terminology
        missed = self._find_missed_terminology(all_matches, expected_terminology)

        # Generate feedback
        feedback = self._generate_feedback(
            all_matches, response_timings, missed, events
        )

        # Count commands and acknowledgments
        total_commands = sum(
            1 for e in events if e.response_type == ResponseType.COMMAND
        )
        acknowledged = sum(
            1 for t in response_timings if t.is_timely
        )

        return CommunicationAnalysisResult(
            asr_result=asr_result,
            events=events,
            terminology_matches=all_matches,
            response_timings=response_timings,
            terminology_score=terminology_score,
            timeliness_score=timeliness_score,
            clarity_score=clarity_score,
            overall_score=overall_score,
            total_commands=total_commands,
            acknowledged_commands=acknowledged,
            missed_terminology=missed,
            feedback=feedback,
        )

    def _find_terminology(self, segment: ASRSegment) -> List[TerminologyMatch]:
        """Find terminology matches in a segment."""
        matches = []
        text = segment.text

        for term_id, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                matched_text = match.group()
                category = self.TERMINOLOGY_CATEGORIES.get(
                    term_id, TerminologyCategory.COMMUNICATION
                )

                matches.append(
                    TerminologyMatch(
                        term_id=term_id,
                        matched_text=matched_text,
                        category=category,
                        start_time=segment.start_time,
                        end_time=segment.end_time,
                        confidence=segment.confidence,
                        is_correct=True,  # Assume correct if matched
                    )
                )

        return matches

    def _classify_response(
        self,
        text: str,
        matches: List[TerminologyMatch],
    ) -> ResponseType:
        """Classify the type of response."""
        text_lower = text.lower()

        # Check for acknowledgment patterns
        ack_patterns = ["收到", "明白", "确认", "roger", "copy", "confirm"]
        if any(p in text_lower for p in ack_patterns):
            return ResponseType.ACKNOWLEDGMENT

        # Check for report patterns
        report_patterns = ["报告", "汇报", "report"]
        if any(p in text_lower for p in report_patterns):
            return ResponseType.REPORT

        # Check for request patterns
        request_patterns = ["请", "需要", "request", "please"]
        if any(p in text_lower for p in request_patterns):
            return ResponseType.REQUEST

        # Check for command-like patterns
        command_categories = [
            TerminologyCategory.EMERGENCY,
            TerminologyCategory.SAFETY,
        ]
        if any(m.category in command_categories for m in matches):
            return ResponseType.COMMAND

        return ResponseType.REPORT

    def _analyze_timings(
        self, events: List[CommunicationEvent]
    ) -> List[ResponseTiming]:
        """Analyze response timing between command and acknowledgment."""
        timings = []

        commands = [
            e for e in events if e.response_type == ResponseType.COMMAND
        ]
        acknowledgments = [
            e for e in events if e.response_type == ResponseType.ACKNOWLEDGMENT
        ]

        for cmd in commands:
            # Find the next acknowledgment after this command
            next_ack = None
            for ack in acknowledgments:
                if ack.start_time > cmd.end_time:
                    next_ack = ack
                    break

            if next_ack:
                delay = next_ack.start_time - cmd.end_time
                time_limit = self._time_limits.get("acknowledgment", 2.0)

                # Check if any terminology matches are emergency type
                is_emergency = any(
                    m.category == TerminologyCategory.EMERGENCY
                    for m in cmd.terminology_matches
                )
                if is_emergency:
                    time_limit = self._time_limits.get("emergency_response", 3.0)

                timings.append(
                    ResponseTiming(
                        trigger_text=cmd.text,
                        trigger_time=cmd.end_time,
                        response_text=next_ack.text,
                        response_time=next_ack.start_time,
                        delay=delay,
                        is_timely=delay <= time_limit,
                        time_limit=time_limit,
                    )
                )

        return timings

    def _calculate_terminology_score(
        self,
        matches: List[TerminologyMatch],
        expected: Optional[Set[str]] = None,
    ) -> float:
        """Calculate terminology usage score (0-100)."""
        if not matches and not expected:
            return 100.0  # No terminology expected or found

        if not matches:
            return 0.0 if expected else 100.0

        # Score based on correct usage
        correct = sum(1 for m in matches if m.is_correct)
        base_score = (correct / len(matches)) * 100 if matches else 0

        # Bonus for finding expected terminology
        if expected:
            found_terms = {m.term_id for m in matches}
            coverage = len(found_terms & expected) / len(expected)
            base_score = base_score * 0.6 + coverage * 100 * 0.4

        return min(100.0, base_score)

    def _calculate_timeliness_score(
        self, timings: List[ResponseTiming]
    ) -> float:
        """Calculate response timeliness score (0-100)."""
        if not timings:
            return 100.0  # No responses to evaluate

        timely_count = sum(1 for t in timings if t.is_timely)
        base_score = (timely_count / len(timings)) * 100

        # Deduct points for very late responses
        for timing in timings:
            if not timing.is_timely:
                excess = timing.delay - timing.time_limit
                penalty = min(10, excess * 5)  # Max 10 point penalty per response
                base_score -= penalty

        return max(0.0, base_score)

    def _calculate_clarity_score(
        self,
        asr_result: ASRResult,
        events: List[CommunicationEvent],
    ) -> float:
        """Calculate communication clarity score (0-100)."""
        if not events:
            return 100.0

        # Based on confidence and clarity of events
        clear_count = sum(1 for e in events if e.is_clear)
        base_score = (clear_count / len(events)) * 100

        # Factor in overall ASR confidence
        confidence_factor = asr_result.confidence
        base_score = base_score * 0.7 + confidence_factor * 100 * 0.3

        return min(100.0, base_score)

    def _find_missed_terminology(
        self,
        matches: List[TerminologyMatch],
        expected: Optional[Set[str]] = None,
    ) -> List[str]:
        """Find expected terminology that was missed."""
        if not expected:
            return []

        found_terms = {m.term_id for m in matches}
        missed = expected - found_terms

        return list(missed)

    def _generate_feedback(
        self,
        matches: List[TerminologyMatch],
        timings: List[ResponseTiming],
        missed: List[str],
        events: List[CommunicationEvent],
    ) -> List[str]:
        """Generate human-readable feedback."""
        feedback = []

        # Terminology feedback
        if matches:
            correct = sum(1 for m in matches if m.is_correct)
            feedback.append(f"使用了 {len(matches)} 个标准术语，{correct} 个正确")

        if missed:
            term_names = {
                "brace": "防冲击指令",
                "evacuate": "撤离指令",
                "fire": "火警术语",
                "confirm": "确认术语",
                "ready": "准备完毕术语",
            }
            missed_names = [term_names.get(t, t) for t in missed]
            feedback.append(f"缺少以下术语: {', '.join(missed_names)}")

        # Timing feedback
        late_responses = [t for t in timings if not t.is_timely]
        if late_responses:
            for timing in late_responses:
                feedback.append(
                    f"响应延迟: '{timing.trigger_text[:20]}...' "
                    f"应答延迟 {timing.delay:.1f} 秒，超过标准 {timing.time_limit:.1f} 秒"
                )
        elif timings:
            feedback.append("所有指令响应及时")

        # Clarity feedback
        unclear = [e for e in events if not e.is_clear]
        if unclear:
            feedback.append(f"{len(unclear)} 处通讯不够清晰，建议提高发音清晰度")

        return feedback

    def add_terminology(self, term_id: str, variations: List[str]) -> None:
        """Add custom terminology."""
        self._terminology[term_id] = variations
        self._build_patterns()

    def set_time_limit(self, response_type: str, limit: float) -> None:
        """Set custom time limit for a response type."""
        self._time_limits[response_type] = limit

    def detect_keywords(
        self,
        text: str,
        keywords: Optional[List[str]] = None,
    ) -> List[Tuple[str, str]]:
        """
        Detect specific keywords in text.

        Useful for trigger detection (e.g., "brace" command).

        Args:
            text: Text to search
            keywords: Specific keywords to find, or None for all

        Returns:
            List of (term_id, matched_text) tuples
        """
        results = []
        text_lower = text.lower()

        for term_id, variations in self._terminology.items():
            if keywords and term_id not in keywords:
                continue

            for var in variations:
                if var.lower() in text_lower:
                    results.append((term_id, var))
                    break

        return results

    def get_terminology(self) -> Dict[str, List[str]]:
        """Get current terminology dictionary."""
        return self._terminology.copy()
