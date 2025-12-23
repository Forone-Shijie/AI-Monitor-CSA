"""
Scenario Trigger - Detects and manages scenario triggers.

Monitors multiple input sources to detect scenario triggers:
- Voice commands (ASR keyword detection)
- System events (API triggers)
- Posture changes (sudden movement detection)
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Set, Tuple

from .sop_analyzer import TriggerType


class TriggerSource(Enum):
    """Source of trigger detection."""

    ASR = "asr"  # From speech recognition
    EVENT_API = "event_api"  # From system event API
    POSE_CHANGE = "pose_change"  # From posture analysis
    MANUAL = "manual"  # Manual trigger


@dataclass
class TriggerEvent:
    """A detected trigger event."""

    scenario_id: str
    trigger_type: TriggerType
    source: TriggerSource
    timestamp: float
    confidence: float = 1.0

    # Source-specific data
    keyword: Optional[str] = None  # For voice triggers
    event_name: Optional[str] = None  # For system events
    pose_change: Optional[str] = None  # For posture triggers

    # Additional context
    text: Optional[str] = None  # Full text for ASR
    metadata: Dict = field(default_factory=dict)


class ScenarioTriggerDetector:
    """
    Detects scenario triggers from multiple sources.

    Monitors:
    - ASR results for trigger keywords
    - System events for trigger signals
    - Pose changes for movement-based triggers

    Usage:
        detector = ScenarioTriggerDetector()

        # Register scenarios
        detector.register_scenario(
            scenario_id="brace_position",
            keywords=["brace", "防冲击", "防冲击姿势"],
            events=["emergency_landing"],
        )

        # Check for triggers
        trigger = detector.check_asr(asr_result)
        if trigger:
            print(f"Triggered: {trigger.scenario_id}")
            # Start scenario monitoring

        # Or use callback
        detector.on_trigger(callback=handle_trigger)
    """

    def __init__(
        self,
        cooldown: float = 5.0,
        min_confidence: float = 0.5,
    ) -> None:
        """
        Initialize trigger detector.

        Args:
            cooldown: Minimum time between same scenario triggers
            min_confidence: Minimum confidence for ASR triggers
        """
        self._cooldown = cooldown
        self._min_confidence = min_confidence

        # Scenario definitions
        self._scenario_keywords: Dict[str, Set[str]] = {}
        self._scenario_events: Dict[str, Set[str]] = {}
        self._keyword_to_scenario: Dict[str, str] = {}
        self._event_to_scenario: Dict[str, str] = {}

        # Trigger history
        self._last_trigger: Dict[str, float] = {}
        self._trigger_history: List[TriggerEvent] = []

        # Callbacks
        self._callbacks: List[Callable[[TriggerEvent], None]] = []

        # Posture monitoring
        self._pose_baseline: Optional[Dict] = None
        self._pose_threshold = 0.3  # Movement threshold for trigger

    def register_scenario(
        self,
        scenario_id: str,
        keywords: Optional[List[str]] = None,
        events: Optional[List[str]] = None,
    ) -> None:
        """
        Register a scenario with its triggers.

        Args:
            scenario_id: Unique scenario identifier
            keywords: List of trigger keywords (for ASR)
            events: List of trigger events (for system events)
        """
        if keywords:
            self._scenario_keywords[scenario_id] = set(
                k.lower() for k in keywords
            )
            for keyword in keywords:
                self._keyword_to_scenario[keyword.lower()] = scenario_id

        if events:
            self._scenario_events[scenario_id] = set(events)
            for event in events:
                self._event_to_scenario[event] = scenario_id

    def unregister_scenario(self, scenario_id: str) -> None:
        """Unregister a scenario."""
        # Remove keywords
        keywords = self._scenario_keywords.pop(scenario_id, set())
        for keyword in keywords:
            self._keyword_to_scenario.pop(keyword, None)

        # Remove events
        events = self._scenario_events.pop(scenario_id, set())
        for event in events:
            self._event_to_scenario.pop(event, None)

    def check_asr(
        self,
        text: str,
        timestamp: Optional[float] = None,
        confidence: float = 1.0,
    ) -> Optional[TriggerEvent]:
        """
        Check ASR text for trigger keywords.

        Args:
            text: Transcribed text to check
            timestamp: When the text was spoken
            confidence: ASR confidence score

        Returns:
            TriggerEvent if trigger detected, None otherwise
        """
        if confidence < self._min_confidence:
            return None

        ts = timestamp or time.time()
        text_lower = text.lower()

        for keyword, scenario_id in self._keyword_to_scenario.items():
            if keyword in text_lower:
                # Check cooldown
                if not self._check_cooldown(scenario_id, ts):
                    continue

                trigger = TriggerEvent(
                    scenario_id=scenario_id,
                    trigger_type=TriggerType.VOICE,
                    source=TriggerSource.ASR,
                    timestamp=ts,
                    confidence=confidence,
                    keyword=keyword,
                    text=text,
                )

                self._record_trigger(trigger)
                return trigger

        return None

    def check_event(
        self,
        event_name: str,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[TriggerEvent]:
        """
        Check system event for trigger.

        Args:
            event_name: Name of the system event
            timestamp: When the event occurred
            metadata: Additional event data

        Returns:
            TriggerEvent if trigger detected, None otherwise
        """
        ts = timestamp or time.time()

        scenario_id = self._event_to_scenario.get(event_name)
        if scenario_id is None:
            return None

        # Check cooldown
        if not self._check_cooldown(scenario_id, ts):
            return None

        trigger = TriggerEvent(
            scenario_id=scenario_id,
            trigger_type=TriggerType.EVENT,
            source=TriggerSource.EVENT_API,
            timestamp=ts,
            confidence=1.0,
            event_name=event_name,
            metadata=metadata or {},
        )

        self._record_trigger(trigger)
        return trigger

    def check_pose_change(
        self,
        pose_data: Dict,
        timestamp: Optional[float] = None,
        scenario_id: Optional[str] = None,
    ) -> Optional[TriggerEvent]:
        """
        Check for sudden posture change as trigger.

        Args:
            pose_data: Current pose data
            timestamp: When the pose was detected
            scenario_id: Optional specific scenario to trigger

        Returns:
            TriggerEvent if significant change detected
        """
        ts = timestamp or time.time()

        if self._pose_baseline is None:
            self._pose_baseline = pose_data
            return None

        # Calculate pose difference
        diff = self._calculate_pose_diff(self._pose_baseline, pose_data)

        if diff > self._pose_threshold:
            # Update baseline
            self._pose_baseline = pose_data

            # Determine scenario (if not specified, use first registered)
            if scenario_id is None:
                scenario_id = next(iter(self._scenario_keywords), None)

            if scenario_id and self._check_cooldown(scenario_id, ts):
                trigger = TriggerEvent(
                    scenario_id=scenario_id,
                    trigger_type=TriggerType.POSTURE,
                    source=TriggerSource.POSE_CHANGE,
                    timestamp=ts,
                    confidence=min(1.0, diff / self._pose_threshold),
                    pose_change=f"Movement detected: {diff:.2f}",
                    metadata={"diff": diff},
                )

                self._record_trigger(trigger)
                return trigger

        return None

    def _calculate_pose_diff(
        self,
        baseline: Dict,
        current: Dict,
    ) -> float:
        """Calculate difference between two poses."""
        # Simple implementation - can be enhanced
        total_diff = 0.0
        count = 0

        for key in baseline:
            if key in current:
                if isinstance(baseline[key], (int, float)):
                    total_diff += abs(baseline[key] - current[key])
                    count += 1

        return total_diff / count if count > 0 else 0.0

    def _check_cooldown(self, scenario_id: str, timestamp: float) -> bool:
        """Check if scenario is past cooldown period."""
        last = self._last_trigger.get(scenario_id, 0)
        return (timestamp - last) >= self._cooldown

    def _record_trigger(self, trigger: TriggerEvent) -> None:
        """Record trigger and notify callbacks."""
        self._last_trigger[trigger.scenario_id] = trigger.timestamp
        self._trigger_history.append(trigger)

        # Trim history
        if len(self._trigger_history) > 100:
            self._trigger_history = self._trigger_history[-50:]

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(trigger)
            except Exception:
                pass

    def trigger_manual(
        self,
        scenario_id: str,
        timestamp: Optional[float] = None,
    ) -> TriggerEvent:
        """
        Manually trigger a scenario.

        Args:
            scenario_id: Scenario to trigger
            timestamp: Optional trigger time

        Returns:
            TriggerEvent for the manual trigger
        """
        ts = timestamp or time.time()

        trigger = TriggerEvent(
            scenario_id=scenario_id,
            trigger_type=TriggerType.MANUAL,
            source=TriggerSource.MANUAL,
            timestamp=ts,
            confidence=1.0,
        )

        self._record_trigger(trigger)
        return trigger

    def on_trigger(
        self,
        callback: Callable[[TriggerEvent], None],
    ) -> None:
        """Register a callback for trigger events."""
        self._callbacks.append(callback)

    def remove_callback(
        self,
        callback: Callable[[TriggerEvent], None],
    ) -> None:
        """Remove a trigger callback."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass

    def get_history(
        self,
        scenario_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[TriggerEvent]:
        """
        Get trigger history.

        Args:
            scenario_id: Filter by scenario
            limit: Maximum events to return

        Returns:
            List of TriggerEvent objects
        """
        if scenario_id:
            filtered = [
                t for t in self._trigger_history
                if t.scenario_id == scenario_id
            ]
            return filtered[-limit:]
        return self._trigger_history[-limit:]

    def get_registered_scenarios(self) -> List[str]:
        """Get list of registered scenario IDs."""
        all_ids = set(self._scenario_keywords.keys())
        all_ids.update(self._scenario_events.keys())
        return list(all_ids)

    def set_cooldown(self, cooldown: float) -> None:
        """Set cooldown period."""
        self._cooldown = cooldown

    def set_pose_threshold(self, threshold: float) -> None:
        """Set pose change threshold."""
        self._pose_threshold = threshold

    def reset_pose_baseline(self) -> None:
        """Reset pose baseline for change detection."""
        self._pose_baseline = None

    def clear_history(self) -> None:
        """Clear trigger history."""
        self._trigger_history.clear()
        self._last_trigger.clear()
