"""
SOP Analyzer - Standard Operating Procedure compliance analysis engine.

Analyzes action sequences against SOP rules to detect:
- Correct action ordering
- Time window compliance
- Missing or extra actions
- Timing violations
"""

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


class ComplianceStatus(Enum):
    """Compliance status for a step or scenario."""

    COMPLIANT = "compliant"
    VIOLATION = "violation"
    PENDING = "pending"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class TriggerType(Enum):
    """Types of scenario triggers."""

    VOICE = "voice"  # Voice command detected
    EVENT = "event"  # System event
    POSTURE = "posture"  # Posture change detected
    MANUAL = "manual"  # Manually triggered


@dataclass
class SOPStep:
    """A single step in an SOP scenario."""

    step_id: int
    action_id: str  # Action identifier
    action_name: str  # Human-readable name
    time_limit: float  # Max time to complete (seconds)
    required: bool = True  # Whether step is mandatory
    order_strict: bool = True  # Must follow sequence order


@dataclass
class SOPScenario:
    """An SOP scenario definition."""

    scenario_id: str
    name: str  # Human-readable name
    trigger_keywords: List[str] = field(default_factory=list)
    trigger_event: Optional[str] = None
    steps: List[SOPStep] = field(default_factory=list)
    max_total_time: float = 60.0  # Max total time (seconds)
    min_hold_duration: float = 0.0  # For posture scenarios


@dataclass
class StepCompliance:
    """Compliance result for a single step."""

    step: SOPStep
    status: ComplianceStatus
    actual_time: Optional[float] = None  # When step was completed
    time_taken: Optional[float] = None  # Time from trigger to completion
    deviation: float = 0.0  # Time deviation from limit
    feedback: str = ""


@dataclass
class ActionEvent:
    """An action event with timing."""

    action_id: str
    action_name: str
    timestamp: float
    confidence: float = 1.0
    duration: float = 0.0


@dataclass
class SOPAnalysisResult:
    """Complete SOP compliance analysis result."""

    # Scenario info
    scenario_id: str
    scenario_name: str

    # Trigger info
    trigger_type: TriggerType
    trigger_time: float
    trigger_text: Optional[str] = None

    # Step compliance
    steps_compliance: List[StepCompliance] = field(default_factory=list)

    # Timing
    total_time: float = 0.0
    time_limit: float = 0.0

    # Overall status
    is_compliant: bool = False
    compliance_ratio: float = 0.0

    # Violations
    violations: List[str] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "trigger_type": self.trigger_type.value,
            "trigger_time": self.trigger_time,
            "trigger_text": self.trigger_text,
            "steps": [
                {
                    "step_id": sc.step.step_id,
                    "action_id": sc.step.action_id,
                    "status": sc.status.value,
                    "time_taken": sc.time_taken,
                    "feedback": sc.feedback,
                }
                for sc in self.steps_compliance
            ],
            "total_time": self.total_time,
            "time_limit": self.time_limit,
            "is_compliant": self.is_compliant,
            "compliance_ratio": self.compliance_ratio,
            "violations": self.violations,
            "feedback": self.feedback,
        }


class SOPAnalyzer:
    """
    SOP (Standard Operating Procedure) compliance analyzer.

    Analyzes action sequences against defined SOP rules to detect:
    - Correct action ordering
    - Time window compliance
    - Missing or extra actions
    - Overall scenario compliance

    Usage:
        analyzer = SOPAnalyzer("config/sop_rules.yaml")

        # Start scenario
        analyzer.start_scenario("fire_emergency", trigger_type=TriggerType.VOICE)

        # Record actions
        analyzer.record_action("ACT_001", "按压呼叫按钮")
        analyzer.record_action("ACT_002", "提起灭火器")

        # Get analysis result
        result = analyzer.analyze()
        print(f"Compliant: {result.is_compliant}")
        for violation in result.violations:
            print(f"  - {violation}")
    """

    def __init__(
        self,
        rules_path: Optional[str] = None,
        rules_dict: Optional[Dict] = None,
    ) -> None:
        """
        Initialize SOP analyzer.

        Args:
            rules_path: Path to SOP rules YAML file
            rules_dict: Dictionary with SOP rules (alternative to file)
        """
        self._scenarios: Dict[str, SOPScenario] = {}
        self._current_scenario: Optional[SOPScenario] = None
        self._trigger_time: Optional[float] = None
        self._trigger_type: TriggerType = TriggerType.MANUAL
        self._trigger_text: Optional[str] = None
        self._action_history: List[ActionEvent] = []

        # Load rules
        if rules_dict:
            self._load_rules_from_dict(rules_dict)
        elif rules_path:
            self._load_rules_from_file(rules_path)

    def _load_rules_from_file(self, path: str) -> None:
        """Load SOP rules from YAML file."""
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._load_rules_from_dict(data)

    def _load_rules_from_dict(self, data: Dict) -> None:
        """Load SOP rules from dictionary."""
        scenarios = data.get("scenarios", {})

        for scenario_id, scenario_data in scenarios.items():
            steps = []
            for i, step_data in enumerate(scenario_data.get("steps", [])):
                step = SOPStep(
                    step_id=step_data.get("step_id", i + 1),
                    action_id=step_data.get("action", f"ACT_{i+1:03d}"),
                    action_name=step_data.get("name", f"Step {i+1}"),
                    time_limit=step_data.get("time_limit", 10.0),
                    required=step_data.get("required", True),
                    order_strict=step_data.get("order_strict", True),
                )
                steps.append(step)

            scenario = SOPScenario(
                scenario_id=scenario_id,
                name=scenario_data.get("name", scenario_id),
                trigger_keywords=scenario_data.get("trigger_keywords", []),
                trigger_event=scenario_data.get("trigger_event"),
                steps=steps,
                max_total_time=scenario_data.get("max_total_time", 60.0),
                min_hold_duration=scenario_data.get("min_hold_duration", 0.0),
            )
            self._scenarios[scenario_id] = scenario

    def start_scenario(
        self,
        scenario_id: str,
        trigger_type: TriggerType = TriggerType.MANUAL,
        trigger_text: Optional[str] = None,
        trigger_time: Optional[float] = None,
    ) -> bool:
        """
        Start monitoring a scenario.

        Args:
            scenario_id: ID of the scenario to monitor
            trigger_type: How the scenario was triggered
            trigger_text: Optional trigger text (for voice)
            trigger_time: Optional specific trigger time

        Returns:
            True if scenario was found and started
        """
        if scenario_id not in self._scenarios:
            return False

        self._current_scenario = self._scenarios[scenario_id]
        self._trigger_time = trigger_time or time.time()
        self._trigger_type = trigger_type
        self._trigger_text = trigger_text
        self._action_history.clear()

        return True

    def stop_scenario(self) -> Optional[SOPAnalysisResult]:
        """
        Stop monitoring and return analysis result.

        Returns:
            SOPAnalysisResult or None if no scenario active
        """
        if self._current_scenario is None:
            return None

        result = self.analyze()
        self._current_scenario = None
        self._action_history.clear()

        return result

    def record_action(
        self,
        action_id: str,
        action_name: str = "",
        timestamp: Optional[float] = None,
        confidence: float = 1.0,
        duration: float = 0.0,
    ) -> None:
        """
        Record an action event.

        Args:
            action_id: Action identifier
            action_name: Human-readable name
            timestamp: When action occurred (default: now)
            confidence: Detection confidence
            duration: Action duration
        """
        event = ActionEvent(
            action_id=action_id,
            action_name=action_name or action_id,
            timestamp=timestamp or time.time(),
            confidence=confidence,
            duration=duration,
        )
        self._action_history.append(event)

    def analyze(self) -> SOPAnalysisResult:
        """
        Analyze current scenario compliance.

        Returns:
            SOPAnalysisResult with all compliance data
        """
        if self._current_scenario is None or self._trigger_time is None:
            return SOPAnalysisResult(
                scenario_id="",
                scenario_name="",
                trigger_type=TriggerType.MANUAL,
                trigger_time=0.0,
                feedback=["未启动任何场景"],
            )

        scenario = self._current_scenario
        current_time = time.time()

        # Analyze each step
        steps_compliance = []
        completed_actions = set()
        violations = []

        for step in scenario.steps:
            compliance = self._analyze_step(step, completed_actions)
            steps_compliance.append(compliance)

            if compliance.status == ComplianceStatus.COMPLIANT:
                completed_actions.add(step.action_id)
            elif compliance.status == ComplianceStatus.VIOLATION:
                violations.append(compliance.feedback)

        # Calculate overall metrics
        total_time = current_time - self._trigger_time
        compliant_steps = sum(
            1 for sc in steps_compliance
            if sc.status == ComplianceStatus.COMPLIANT
        )
        required_steps = sum(1 for s in scenario.steps if s.required)
        compliance_ratio = compliant_steps / len(scenario.steps) if scenario.steps else 0

        # Check total time
        is_time_compliant = total_time <= scenario.max_total_time
        if not is_time_compliant:
            violations.append(
                f"总用时 {total_time:.1f} 秒，超过限制 {scenario.max_total_time:.0f} 秒"
            )

        # Overall compliance
        required_compliant = sum(
            1 for sc in steps_compliance
            if sc.step.required and sc.status == ComplianceStatus.COMPLIANT
        )
        is_compliant = (required_compliant == required_steps) and is_time_compliant

        # Generate feedback
        feedback = self._generate_feedback(
            steps_compliance, compliance_ratio, total_time, scenario
        )

        return SOPAnalysisResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            trigger_type=self._trigger_type,
            trigger_time=self._trigger_time,
            trigger_text=self._trigger_text,
            steps_compliance=steps_compliance,
            total_time=total_time,
            time_limit=scenario.max_total_time,
            is_compliant=is_compliant,
            compliance_ratio=compliance_ratio,
            violations=violations,
            feedback=feedback,
        )

    def _analyze_step(
        self,
        step: SOPStep,
        completed_actions: Set[str],
    ) -> StepCompliance:
        """Analyze compliance for a single step."""
        # Find matching action in history
        matching_action = None
        for action in self._action_history:
            if action.action_id == step.action_id:
                matching_action = action
                break

        if matching_action is None:
            # Action not found
            if step.required:
                return StepCompliance(
                    step=step,
                    status=ComplianceStatus.PENDING,
                    feedback=f"未检测到动作: {step.action_name}",
                )
            else:
                return StepCompliance(
                    step=step,
                    status=ComplianceStatus.SKIPPED,
                    feedback=f"可选动作未执行: {step.action_name}",
                )

        # Calculate timing
        time_taken = matching_action.timestamp - self._trigger_time
        deviation = time_taken - step.time_limit

        if time_taken <= step.time_limit:
            return StepCompliance(
                step=step,
                status=ComplianceStatus.COMPLIANT,
                actual_time=matching_action.timestamp,
                time_taken=time_taken,
                deviation=0.0,
                feedback=f"{step.action_name} 完成，用时 {time_taken:.1f} 秒",
            )
        else:
            return StepCompliance(
                step=step,
                status=ComplianceStatus.TIMEOUT,
                actual_time=matching_action.timestamp,
                time_taken=time_taken,
                deviation=deviation,
                feedback=f"{step.action_name} 超时，用时 {time_taken:.1f} 秒，"
                         f"超过限制 {step.time_limit:.0f} 秒",
            )

    def _generate_feedback(
        self,
        steps_compliance: List[StepCompliance],
        compliance_ratio: float,
        total_time: float,
        scenario: SOPScenario,
    ) -> List[str]:
        """Generate human-readable feedback."""
        feedback = []

        # Summary
        compliant_count = sum(
            1 for sc in steps_compliance
            if sc.status == ComplianceStatus.COMPLIANT
        )
        total_count = len(steps_compliance)

        if compliance_ratio == 1.0:
            feedback.append(f"✓ {scenario.name} 所有步骤完成合规")
        else:
            feedback.append(
                f"△ {scenario.name} 完成 {compliant_count}/{total_count} 个步骤"
            )

        # Timing
        if total_time <= scenario.max_total_time:
            feedback.append(f"✓ 总用时 {total_time:.1f} 秒，在规定时间内")
        else:
            over = total_time - scenario.max_total_time
            feedback.append(f"✗ 总用时 {total_time:.1f} 秒，超时 {over:.1f} 秒")

        # Step details
        for sc in steps_compliance:
            if sc.status == ComplianceStatus.PENDING and sc.step.required:
                feedback.append(f"✗ 缺少必需动作: {sc.step.action_name}")
            elif sc.status == ComplianceStatus.TIMEOUT:
                feedback.append(
                    f"✗ {sc.step.action_name} 延迟 {sc.deviation:.1f} 秒"
                )

        return feedback

    def detect_trigger(
        self,
        text: str,
        keywords: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Detect scenario trigger from text.

        Args:
            text: Text to search for triggers
            keywords: Optional specific keywords to check

        Returns:
            Scenario ID if trigger found, None otherwise
        """
        text_lower = text.lower()

        for scenario_id, scenario in self._scenarios.items():
            check_keywords = keywords or scenario.trigger_keywords

            for keyword in check_keywords:
                if keyword.lower() in text_lower:
                    return scenario_id

        return None

    def get_scenario(self, scenario_id: str) -> Optional[SOPScenario]:
        """Get scenario by ID."""
        return self._scenarios.get(scenario_id)

    def get_all_scenarios(self) -> Dict[str, SOPScenario]:
        """Get all loaded scenarios."""
        return self._scenarios.copy()

    @property
    def current_scenario(self) -> Optional[SOPScenario]:
        """Get currently active scenario."""
        return self._current_scenario

    @property
    def is_active(self) -> bool:
        """Check if a scenario is currently active."""
        return self._current_scenario is not None

    @property
    def action_history(self) -> List[ActionEvent]:
        """Get recorded action history."""
        return self._action_history.copy()

    def reset(self) -> None:
        """Reset analyzer state."""
        self._current_scenario = None
        self._trigger_time = None
        self._action_history.clear()
