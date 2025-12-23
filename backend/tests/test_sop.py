"""
Phase 5 Tests - SOP Analysis, Synchronizer, and Scenario Trigger Detection.

Tests for:
- SOPAnalyzer: SOP compliance analysis
- Synchronizer: Multi-modal data alignment
- ScenarioTriggerDetector: Trigger detection from multiple sources
"""

import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.analysis import (
    ActionEvent,
    ArmPosition,
    BodyPartStatus,
    BracePositionResult,
    ComplianceStatus,
    DataType,
    HeadPosition,
    ScenarioTriggerDetector,
    SOPAnalysisResult,
    SOPAnalyzer,
    SOPScenario,
    SOPStep,
    StepCompliance,
    SyncedFrame,
    Synchronizer,
    TimestampedData,
    TriggerEvent,
    TriggerSource,
    TriggerType,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_sop_rules():
    """Sample SOP rules for testing."""
    return {
        "scenarios": {
            "brace_position": {
                "name": "防冲击姿势",
                "trigger_keywords": ["brace", "防冲击", "防冲击姿势"],
                "trigger_event": "emergency_landing",
                "max_total_time": 30.0,
                "min_hold_duration": 5.0,
                "steps": [
                    {
                        "step_id": 1,
                        "action": "ACT_001",
                        "name": "弯腰低头",
                        "time_limit": 5.0,
                        "required": True,
                    },
                    {
                        "step_id": 2,
                        "action": "ACT_002",
                        "name": "双手抱头",
                        "time_limit": 3.0,
                        "required": True,
                    },
                    {
                        "step_id": 3,
                        "action": "ACT_003",
                        "name": "保持姿势",
                        "time_limit": 20.0,
                        "required": True,
                    },
                ],
            },
            "fire_emergency": {
                "name": "火警处置",
                "trigger_keywords": ["fire", "火警", "着火"],
                "trigger_event": "fire_alarm",
                "max_total_time": 60.0,
                "steps": [
                    {
                        "step_id": 1,
                        "action": "ACT_101",
                        "name": "按压呼叫按钮",
                        "time_limit": 5.0,
                        "required": True,
                    },
                    {
                        "step_id": 2,
                        "action": "ACT_102",
                        "name": "提起灭火器",
                        "time_limit": 10.0,
                        "required": True,
                    },
                    {
                        "step_id": 3,
                        "action": "ACT_103",
                        "name": "拔除保险销",
                        "time_limit": 5.0,
                        "required": True,
                    },
                ],
            },
        }
    }


@pytest.fixture
def sop_analyzer(sample_sop_rules):
    """Create SOP analyzer with sample rules."""
    return SOPAnalyzer(rules_dict=sample_sop_rules)


@pytest.fixture
def synchronizer():
    """Create synchronizer with default settings."""
    return Synchronizer(tolerance=0.1, max_buffer_size=100)


@pytest.fixture
def trigger_detector():
    """Create trigger detector with sample scenarios."""
    detector = ScenarioTriggerDetector(cooldown=1.0, min_confidence=0.5)
    detector.register_scenario(
        scenario_id="brace_position",
        keywords=["brace", "防冲击", "防冲击姿势"],
        events=["emergency_landing"],
    )
    detector.register_scenario(
        scenario_id="fire_emergency",
        keywords=["fire", "火警"],
        events=["fire_alarm"],
    )
    return detector


# =============================================================================
# SOPAnalyzer Tests
# =============================================================================


class TestSOPAnalyzer:
    """Tests for SOPAnalyzer."""

    def test_init_with_rules_dict(self, sample_sop_rules):
        """Test initialization with rules dictionary."""
        analyzer = SOPAnalyzer(rules_dict=sample_sop_rules)

        scenarios = analyzer.get_all_scenarios()
        assert len(scenarios) == 2
        assert "brace_position" in scenarios
        assert "fire_emergency" in scenarios

    def test_init_with_invalid_file(self):
        """Test initialization with non-existent file."""
        analyzer = SOPAnalyzer(rules_path="/non/existent/path.yaml")
        assert len(analyzer.get_all_scenarios()) == 0

    def test_get_scenario(self, sop_analyzer):
        """Test getting scenario by ID."""
        scenario = sop_analyzer.get_scenario("brace_position")

        assert scenario is not None
        assert scenario.name == "防冲击姿势"
        assert len(scenario.steps) == 3
        assert scenario.max_total_time == 30.0

    def test_get_scenario_not_found(self, sop_analyzer):
        """Test getting non-existent scenario."""
        scenario = sop_analyzer.get_scenario("non_existent")
        assert scenario is None

    def test_start_scenario(self, sop_analyzer):
        """Test starting a scenario."""
        result = sop_analyzer.start_scenario(
            "brace_position",
            trigger_type=TriggerType.VOICE,
            trigger_text="brace for impact",
        )

        assert result is True
        assert sop_analyzer.is_active
        assert sop_analyzer.current_scenario.scenario_id == "brace_position"

    def test_start_scenario_not_found(self, sop_analyzer):
        """Test starting non-existent scenario."""
        result = sop_analyzer.start_scenario("non_existent")

        assert result is False
        assert not sop_analyzer.is_active

    def test_record_action(self, sop_analyzer):
        """Test recording actions."""
        sop_analyzer.start_scenario("brace_position")

        sop_analyzer.record_action("ACT_001", "弯腰低头", confidence=0.95)
        sop_analyzer.record_action("ACT_002", "双手抱头", confidence=0.90)

        history = sop_analyzer.action_history
        assert len(history) == 2
        assert history[0].action_id == "ACT_001"
        assert history[1].action_id == "ACT_002"

    def test_analyze_compliant(self, sop_analyzer):
        """Test analysis with compliant actions."""
        base_time = time.time()

        sop_analyzer.start_scenario(
            "brace_position",
            trigger_type=TriggerType.VOICE,
            trigger_time=base_time,
        )

        # Record actions within time limits (step1: 5s, step2: 3s, step3: 20s)
        sop_analyzer.record_action("ACT_001", "弯腰低头", timestamp=base_time + 2.0)  # within 5s
        sop_analyzer.record_action("ACT_002", "双手抱头", timestamp=base_time + 2.5)  # within 3s
        sop_analyzer.record_action("ACT_003", "保持姿势", timestamp=base_time + 10.0)  # within 20s

        # Patch time.time to return a value within max_total_time
        with patch("time.time", return_value=base_time + 15.0):
            result = sop_analyzer.analyze()

        assert result.scenario_id == "brace_position"
        assert result.is_compliant
        assert result.compliance_ratio == 1.0
        assert len(result.violations) == 0

    def test_analyze_with_timeout(self, sop_analyzer):
        """Test analysis with action timeout."""
        base_time = time.time()

        sop_analyzer.start_scenario(
            "brace_position",
            trigger_time=base_time,
        )

        # Record action after time limit
        sop_analyzer.record_action("ACT_001", "弯腰低头", timestamp=base_time + 10.0)  # Limit is 5s

        with patch("time.time", return_value=base_time + 15.0):
            result = sop_analyzer.analyze()

        # Check step compliance
        step1 = result.steps_compliance[0]
        assert step1.status == ComplianceStatus.TIMEOUT
        assert step1.deviation > 0

    def test_analyze_missing_action(self, sop_analyzer):
        """Test analysis with missing required action."""
        base_time = time.time()

        sop_analyzer.start_scenario(
            "brace_position",
            trigger_time=base_time,
        )

        # Only record first action, skip others
        sop_analyzer.record_action("ACT_001", "弯腰低头", timestamp=base_time + 2.0)

        with patch("time.time", return_value=base_time + 15.0):
            result = sop_analyzer.analyze()

        assert not result.is_compliant
        assert result.compliance_ratio < 1.0

        # Check pending steps
        pending_steps = [
            sc for sc in result.steps_compliance
            if sc.status == ComplianceStatus.PENDING
        ]
        assert len(pending_steps) == 2

    def test_analyze_total_time_exceeded(self, sop_analyzer):
        """Test analysis when total time exceeds limit."""
        base_time = time.time()

        sop_analyzer.start_scenario(
            "brace_position",
            trigger_time=base_time,
        )

        # Record all actions
        sop_analyzer.record_action("ACT_001", "弯腰低头", timestamp=base_time + 2.0)
        sop_analyzer.record_action("ACT_002", "双手抱头", timestamp=base_time + 4.0)
        sop_analyzer.record_action("ACT_003", "保持姿势", timestamp=base_time + 10.0)

        # Total time exceeds 30s limit
        with patch("time.time", return_value=base_time + 35.0):
            result = sop_analyzer.analyze()

        assert not result.is_compliant
        assert any("超过限制" in v for v in result.violations)

    def test_analyze_no_scenario(self, sop_analyzer):
        """Test analysis without active scenario."""
        result = sop_analyzer.analyze()

        assert result.scenario_id == ""
        assert not result.is_compliant

    def test_stop_scenario(self, sop_analyzer):
        """Test stopping a scenario."""
        sop_analyzer.start_scenario("brace_position")
        sop_analyzer.record_action("ACT_001", "弯腰低头")

        result = sop_analyzer.stop_scenario()

        assert result is not None
        assert not sop_analyzer.is_active
        assert len(sop_analyzer.action_history) == 0

    def test_detect_trigger(self, sop_analyzer):
        """Test trigger detection from text."""
        # Test Chinese keyword
        scenario_id = sop_analyzer.detect_trigger("请做好防冲击姿势准备")
        assert scenario_id == "brace_position"

        # Test English keyword
        scenario_id = sop_analyzer.detect_trigger("fire in cabin!")
        assert scenario_id == "fire_emergency"

        # Test no match
        scenario_id = sop_analyzer.detect_trigger("normal operation")
        assert scenario_id is None

    def test_reset(self, sop_analyzer):
        """Test reset functionality."""
        sop_analyzer.start_scenario("brace_position")
        sop_analyzer.record_action("ACT_001", "弯腰低头")

        sop_analyzer.reset()

        assert not sop_analyzer.is_active
        assert len(sop_analyzer.action_history) == 0

    def test_result_to_dict(self, sop_analyzer):
        """Test SOPAnalysisResult serialization."""
        base_time = time.time()

        sop_analyzer.start_scenario(
            "brace_position",
            trigger_type=TriggerType.VOICE,
            trigger_time=base_time,
        )
        sop_analyzer.record_action("ACT_001", "弯腰低头", timestamp=base_time + 2.0)

        with patch("time.time", return_value=base_time + 10.0):
            result = sop_analyzer.analyze()

        result_dict = result.to_dict()

        assert "scenario_id" in result_dict
        assert "steps" in result_dict
        assert "is_compliant" in result_dict
        assert result_dict["trigger_type"] == "voice"


# =============================================================================
# Synchronizer Tests
# =============================================================================


class TestSynchronizer:
    """Tests for Synchronizer."""

    def test_init(self):
        """Test synchronizer initialization."""
        sync = Synchronizer(tolerance=0.2, max_buffer_size=500)

        assert sync.tolerance == 0.2
        assert sync.get_buffer_size(DataType.POSE) == 0

    def test_add_pose(self, synchronizer):
        """Test adding pose data."""
        synchronizer.add_pose(
            timestamp=1.0,
            pose_result={"keypoints": [1, 2, 3]},
            source="mediapipe",
            confidence=0.95,
        )

        assert synchronizer.get_buffer_size(DataType.POSE) == 1

        latest = synchronizer.get_latest(DataType.POSE)
        assert latest is not None
        assert latest.data["keypoints"] == [1, 2, 3]

    def test_add_asr(self, synchronizer):
        """Test adding ASR data."""
        synchronizer.add_asr(
            timestamp=1.0,
            asr_result={"text": "hello world"},
            source="whisper",
            confidence=0.9,
        )

        assert synchronizer.get_buffer_size(DataType.ASR) == 1

    def test_add_action(self, synchronizer):
        """Test adding action data."""
        synchronizer.add_action(
            timestamp=1.0,
            action_event={"action": "wave", "confidence": 0.85},
        )

        assert synchronizer.get_buffer_size(DataType.ACTION) == 1

    def test_add_event(self, synchronizer):
        """Test adding event data."""
        synchronizer.add_event(
            timestamp=1.0,
            event={"type": "trigger", "name": "emergency"},
        )

        assert synchronizer.get_buffer_size(DataType.EVENT) == 1

    def test_get_synced_frame_basic(self, synchronizer):
        """Test getting synchronized frame."""
        # Add data at different times
        synchronizer.add_pose(1.0, {"pose": "a"})
        synchronizer.add_asr(1.05, {"text": "hello"})
        synchronizer.add_action(1.08, {"action": "wave"})

        # Get frame at t=1.0 with 0.1s tolerance
        frame = synchronizer.get_synced_frame(1.0)

        assert frame.has_pose
        assert frame.has_asr
        assert frame.has_action

    def test_get_synced_frame_no_match(self, synchronizer):
        """Test getting frame with no nearby data."""
        synchronizer.add_pose(1.0, {"pose": "a"})

        # Get frame far from data
        frame = synchronizer.get_synced_frame(5.0)

        assert not frame.has_pose
        assert not frame.has_asr

    def test_get_synced_frame_asr_text_extraction(self, synchronizer):
        """Test ASR text extraction in synced frame."""
        # Test with object having text attribute
        class ASRResult:
            text = "hello world"

        synchronizer.add_asr(1.0, ASRResult())
        frame = synchronizer.get_synced_frame(1.0)
        assert frame.asr_text == "hello world"

        # Test with string
        synchronizer.clear()
        synchronizer.add_asr(1.0, "direct text")
        frame = synchronizer.get_synced_frame(1.0)
        assert frame.asr_text == "direct text"

        # Test with dict
        synchronizer.clear()
        synchronizer.add_asr(1.0, {"text": "dict text"})
        frame = synchronizer.get_synced_frame(1.0)
        assert frame.asr_text == "dict text"

    def test_get_frames_in_range(self, synchronizer):
        """Test getting frames in time range."""
        for i in range(10):
            synchronizer.add_pose(float(i), {"frame": i})

        frames = synchronizer.get_frames_in_range(
            start=2.0,
            end=5.0,
            step=1.0,
        )

        assert len(frames) == 4  # 2.0, 3.0, 4.0, 5.0
        assert all(f.has_pose for f in frames)

    def test_buffer_size_limit(self, synchronizer):
        """Test buffer size limiting."""
        # Add more data than buffer size
        for i in range(150):
            synchronizer.add_pose(float(i), {"frame": i})

        # Should be trimmed to max_buffer_size (100)
        assert synchronizer.get_buffer_size(DataType.POSE) == 100

    def test_time_offset(self, synchronizer):
        """Test time offset functionality."""
        # Add data without offset first
        synchronizer.add_pose(1.0, {"pose": "a"})

        # Data should be at time 1.0
        frame = synchronizer.get_synced_frame(1.0)
        assert frame.has_pose

        # Now set offset and add more data
        synchronizer.set_time_offset(0.5)
        synchronizer.add_pose(1.0, {"pose": "b"})  # Will be stored at 1.5

        # Query at 1.5 should find the new data
        frame = synchronizer.get_synced_frame(1.0)  # Queries at 1.5 with offset
        assert frame.has_pose

    def test_tolerance_setting(self, synchronizer):
        """Test tolerance property."""
        synchronizer.tolerance = 0.5
        assert synchronizer.tolerance == 0.5

        synchronizer.add_pose(1.0, {"pose": "a"})

        # Should find with larger tolerance
        frame = synchronizer.get_synced_frame(1.4)
        assert frame.has_pose

        # Should not find with small tolerance override
        frame = synchronizer.get_synced_frame(1.4, tolerance=0.1)
        assert not frame.has_pose

    def test_clear(self, synchronizer):
        """Test clearing all buffers."""
        synchronizer.add_pose(1.0, {"pose": "a"})
        synchronizer.add_asr(1.0, {"text": "hello"})
        synchronizer.add_action(1.0, {"action": "wave"})
        synchronizer.add_event(1.0, {"event": "trigger"})

        synchronizer.clear()

        assert synchronizer.get_buffer_size(DataType.POSE) == 0
        assert synchronizer.get_buffer_size(DataType.ASR) == 0
        assert synchronizer.get_buffer_size(DataType.ACTION) == 0
        assert synchronizer.get_buffer_size(DataType.EVENT) == 0

    def test_callback_registration(self, synchronizer):
        """Test callback registration and notification."""
        received = []

        def callback(data):
            received.append(data)

        synchronizer.register_callback(DataType.POSE, callback)
        synchronizer.add_pose(1.0, {"pose": "test"})

        assert len(received) == 1
        assert received[0]["pose"] == "test"

    def test_callback_unregistration(self, synchronizer):
        """Test callback unregistration."""
        received = []

        def callback(data):
            received.append(data)

        synchronizer.register_callback(DataType.POSE, callback)
        synchronizer.unregister_callback(DataType.POSE, callback)
        synchronizer.add_pose(1.0, {"pose": "test"})

        assert len(received) == 0

    def test_callback_error_handling(self, synchronizer):
        """Test that callback errors don't affect main flow."""
        def bad_callback(data):
            raise ValueError("Test error")

        synchronizer.register_callback(DataType.POSE, bad_callback)

        # Should not raise
        synchronizer.add_pose(1.0, {"pose": "test"})
        assert synchronizer.get_buffer_size(DataType.POSE) == 1

    def test_synced_frame_to_dict(self, synchronizer):
        """Test SyncedFrame serialization."""
        synchronizer.add_pose(1.0, {"pose": "a"})
        synchronizer.add_asr(1.0, {"text": "hello"})
        synchronizer.add_event(1.0, {"event": "trigger"})

        frame = synchronizer.get_synced_frame(1.0)
        frame_dict = frame.to_dict()

        assert "timestamp" in frame_dict
        assert "frame_number" in frame_dict
        assert "has_pose" in frame_dict
        assert frame_dict["has_pose"] is True

    def test_get_latest_empty(self, synchronizer):
        """Test getting latest from empty buffer."""
        latest = synchronizer.get_latest(DataType.POSE)
        assert latest is None

    def test_events_in_range(self, synchronizer):
        """Test getting multiple events in time range."""
        synchronizer.add_event(1.0, {"event": "a"})
        synchronizer.add_event(1.05, {"event": "b"})
        synchronizer.add_event(1.08, {"event": "c"})

        frame = synchronizer.get_synced_frame(1.05, tolerance=0.1)

        # Should capture all events within tolerance
        assert len(frame.events) >= 2


# =============================================================================
# ScenarioTriggerDetector Tests
# =============================================================================


class TestScenarioTriggerDetector:
    """Tests for ScenarioTriggerDetector."""

    def test_init(self):
        """Test detector initialization."""
        detector = ScenarioTriggerDetector(cooldown=2.0, min_confidence=0.7)

        assert len(detector.get_registered_scenarios()) == 0

    def test_register_scenario(self, trigger_detector):
        """Test scenario registration."""
        scenarios = trigger_detector.get_registered_scenarios()

        assert "brace_position" in scenarios
        assert "fire_emergency" in scenarios

    def test_unregister_scenario(self, trigger_detector):
        """Test scenario unregistration."""
        trigger_detector.unregister_scenario("brace_position")

        scenarios = trigger_detector.get_registered_scenarios()
        assert "brace_position" not in scenarios
        assert "fire_emergency" in scenarios

    def test_check_asr_keyword_match(self, trigger_detector):
        """Test ASR keyword detection."""
        trigger = trigger_detector.check_asr(
            text="请做好防冲击姿势",
            timestamp=1.0,
            confidence=0.9,
        )

        assert trigger is not None
        assert trigger.scenario_id == "brace_position"
        assert trigger.trigger_type == TriggerType.VOICE
        assert trigger.source == TriggerSource.ASR
        assert trigger.keyword == "防冲击"

    def test_check_asr_english_keyword(self, trigger_detector):
        """Test English keyword detection."""
        trigger = trigger_detector.check_asr(
            text="Brace for impact!",
            timestamp=1.0,
        )

        assert trigger is not None
        assert trigger.scenario_id == "brace_position"

    def test_check_asr_no_match(self, trigger_detector):
        """Test no keyword match."""
        trigger = trigger_detector.check_asr(
            text="normal conversation",
            timestamp=1.0,
        )

        assert trigger is None

    def test_check_asr_low_confidence(self, trigger_detector):
        """Test low confidence filtering."""
        trigger = trigger_detector.check_asr(
            text="brace for impact",
            confidence=0.3,  # Below min_confidence (0.5)
        )

        assert trigger is None

    def test_check_asr_cooldown(self, trigger_detector):
        """Test cooldown between triggers."""
        # First trigger
        trigger1 = trigger_detector.check_asr(
            text="brace",
            timestamp=1.0,
        )
        assert trigger1 is not None

        # Second trigger within cooldown (1s)
        trigger2 = trigger_detector.check_asr(
            text="brace again",
            timestamp=1.5,
        )
        assert trigger2 is None

        # Third trigger after cooldown
        trigger3 = trigger_detector.check_asr(
            text="brace once more",
            timestamp=2.5,
        )
        assert trigger3 is not None

    def test_check_event(self, trigger_detector):
        """Test event-based trigger."""
        trigger = trigger_detector.check_event(
            event_name="emergency_landing",
            timestamp=1.0,
            metadata={"severity": "high"},
        )

        assert trigger is not None
        assert trigger.scenario_id == "brace_position"
        assert trigger.trigger_type == TriggerType.EVENT
        assert trigger.source == TriggerSource.EVENT_API
        assert trigger.metadata["severity"] == "high"

    def test_check_event_no_match(self, trigger_detector):
        """Test unregistered event."""
        trigger = trigger_detector.check_event(
            event_name="unknown_event",
            timestamp=1.0,
        )

        assert trigger is None

    def test_check_pose_change(self, trigger_detector):
        """Test pose change trigger."""
        # Set baseline
        trigger_detector.check_pose_change(
            pose_data={"x": 0.0, "y": 0.0},
            timestamp=1.0,
        )

        # Significant change
        trigger = trigger_detector.check_pose_change(
            pose_data={"x": 0.5, "y": 0.5},
            timestamp=2.0,
        )

        assert trigger is not None
        assert trigger.trigger_type == TriggerType.POSTURE
        assert trigger.source == TriggerSource.POSE_CHANGE

    def test_check_pose_change_small_movement(self, trigger_detector):
        """Test small pose change (no trigger)."""
        # Set baseline
        trigger_detector.check_pose_change(
            pose_data={"x": 0.0, "y": 0.0},
            timestamp=1.0,
        )

        # Small change (below threshold)
        trigger = trigger_detector.check_pose_change(
            pose_data={"x": 0.1, "y": 0.1},
            timestamp=2.0,
        )

        assert trigger is None

    def test_trigger_manual(self, trigger_detector):
        """Test manual trigger."""
        trigger = trigger_detector.trigger_manual(
            scenario_id="brace_position",
            timestamp=1.0,
        )

        assert trigger is not None
        assert trigger.trigger_type == TriggerType.MANUAL
        assert trigger.source == TriggerSource.MANUAL
        assert trigger.confidence == 1.0

    def test_on_trigger_callback(self, trigger_detector):
        """Test trigger callback."""
        received = []

        def callback(trigger):
            received.append(trigger)

        trigger_detector.on_trigger(callback)
        trigger_detector.check_asr("brace", timestamp=1.0)

        assert len(received) == 1
        assert received[0].scenario_id == "brace_position"

    def test_remove_callback(self, trigger_detector):
        """Test callback removal."""
        received = []

        def callback(trigger):
            received.append(trigger)

        trigger_detector.on_trigger(callback)
        trigger_detector.remove_callback(callback)
        trigger_detector.check_asr("brace", timestamp=1.0)

        assert len(received) == 0

    def test_get_history(self, trigger_detector):
        """Test trigger history."""
        trigger_detector.check_asr("brace", timestamp=1.0)
        trigger_detector.check_asr("fire", timestamp=3.0)  # After cooldown

        # Get all history
        history = trigger_detector.get_history(limit=10)
        assert len(history) == 2

        # Get filtered history
        history = trigger_detector.get_history(
            scenario_id="brace_position",
            limit=10,
        )
        assert len(history) == 1
        assert history[0].scenario_id == "brace_position"

    def test_clear_history(self, trigger_detector):
        """Test clearing history."""
        trigger_detector.check_asr("brace", timestamp=1.0)
        trigger_detector.clear_history()

        history = trigger_detector.get_history()
        assert len(history) == 0

    def test_set_cooldown(self, trigger_detector):
        """Test setting cooldown."""
        trigger_detector.set_cooldown(0.1)

        # Rapid triggers should work with short cooldown
        trigger1 = trigger_detector.check_asr("brace", timestamp=1.0)
        trigger2 = trigger_detector.check_asr("brace", timestamp=1.2)

        assert trigger1 is not None
        assert trigger2 is not None

    def test_set_pose_threshold(self, trigger_detector):
        """Test setting pose threshold."""
        trigger_detector.set_pose_threshold(0.01)  # Very sensitive

        # Set baseline
        trigger_detector.check_pose_change({"x": 0.0}, timestamp=1.0)

        # Small change should trigger now
        trigger = trigger_detector.check_pose_change({"x": 0.05}, timestamp=2.0)
        assert trigger is not None

    def test_reset_pose_baseline(self, trigger_detector):
        """Test resetting pose baseline."""
        # Set initial baseline
        trigger_detector.check_pose_change({"x": 0.0}, timestamp=1.0)

        # Reset baseline
        trigger_detector.reset_pose_baseline()

        # Next check should set new baseline (no trigger)
        trigger = trigger_detector.check_pose_change({"x": 0.5}, timestamp=2.0)
        assert trigger is None

    def test_callback_error_handling(self, trigger_detector):
        """Test callback error doesn't break flow."""
        def bad_callback(trigger):
            raise ValueError("Test error")

        trigger_detector.on_trigger(bad_callback)

        # Should not raise
        trigger = trigger_detector.check_asr("brace", timestamp=1.0)
        assert trigger is not None


# =============================================================================
# Integration Tests
# =============================================================================


class TestSOPIntegration:
    """Integration tests for SOP analysis workflow."""

    def test_full_workflow(self, sample_sop_rules):
        """Test complete SOP analysis workflow."""
        # Setup
        analyzer = SOPAnalyzer(rules_dict=sample_sop_rules)
        synchronizer = Synchronizer(tolerance=0.1)
        detector = ScenarioTriggerDetector(cooldown=1.0)

        detector.register_scenario(
            scenario_id="brace_position",
            keywords=["防冲击"],
        )

        base_time = time.time()

        # Step 1: Detect trigger from ASR
        trigger = detector.check_asr("请做好防冲击姿势", timestamp=base_time)
        assert trigger is not None

        # Step 2: Start scenario
        result = analyzer.start_scenario(
            trigger.scenario_id,
            trigger_type=trigger.trigger_type,
            trigger_text=trigger.text,
            trigger_time=base_time,
        )
        assert result is True

        # Step 3: Record synchronized actions
        synchronizer.add_pose(base_time + 1.0, {"bending": True})
        synchronizer.add_action(base_time + 1.0, {"action": "ACT_001"})

        analyzer.record_action("ACT_001", "弯腰低头", timestamp=base_time + 1.0)
        analyzer.record_action("ACT_002", "双手抱头", timestamp=base_time + 3.0)
        analyzer.record_action("ACT_003", "保持姿势", timestamp=base_time + 8.0)

        # Step 4: Analyze compliance
        with patch("time.time", return_value=base_time + 15.0):
            result = analyzer.analyze()

        assert result.is_compliant
        assert result.compliance_ratio == 1.0

        # Step 5: Get synchronized frame for review
        frame = synchronizer.get_synced_frame(base_time + 1.0)
        assert frame.has_pose
        assert frame.has_action

    def test_trigger_to_analysis_flow(self, sample_sop_rules):
        """Test flow from trigger detection to analysis."""
        analyzer = SOPAnalyzer(rules_dict=sample_sop_rules)
        detector = ScenarioTriggerDetector()

        detector.register_scenario(
            scenario_id="fire_emergency",
            keywords=["火警"],
            events=["fire_alarm"],
        )

        base_time = time.time()

        # Event trigger
        trigger = detector.check_event("fire_alarm", timestamp=base_time)
        assert trigger is not None

        # Start and record actions
        analyzer.start_scenario(
            trigger.scenario_id,
            trigger_type=trigger.trigger_type,
            trigger_time=base_time,
        )

        analyzer.record_action("ACT_101", "按压呼叫按钮", timestamp=base_time + 3.0)
        analyzer.record_action("ACT_102", "提起灭火器", timestamp=base_time + 8.0)
        # Missing ACT_103

        with patch("time.time", return_value=base_time + 30.0):
            result = analyzer.analyze()

        # Should not be compliant due to missing step
        assert not result.is_compliant
        assert result.compliance_ratio < 1.0


# =============================================================================
# Data Class Tests
# =============================================================================


class TestDataClasses:
    """Tests for data classes."""

    def test_trigger_event(self):
        """Test TriggerEvent dataclass."""
        event = TriggerEvent(
            scenario_id="test",
            trigger_type=TriggerType.VOICE,
            source=TriggerSource.ASR,
            timestamp=1.0,
            confidence=0.95,
            keyword="brace",
            text="brace for impact",
        )

        assert event.scenario_id == "test"
        assert event.confidence == 0.95
        assert event.metadata == {}

    def test_timestamped_data(self):
        """Test TimestampedData dataclass."""
        data = TimestampedData(
            timestamp=1.0,
            data={"test": "value"},
            data_type=DataType.POSE,
            source="mediapipe",
            confidence=0.9,
        )

        assert data.timestamp == 1.0
        assert data.data_type == DataType.POSE

    def test_action_event(self):
        """Test ActionEvent dataclass."""
        event = ActionEvent(
            action_id="ACT_001",
            action_name="Test Action",
            timestamp=1.0,
            confidence=0.95,
            duration=2.0,
        )

        assert event.action_id == "ACT_001"
        assert event.duration == 2.0

    def test_sop_step(self):
        """Test SOPStep dataclass."""
        step = SOPStep(
            step_id=1,
            action_id="ACT_001",
            action_name="Test Step",
            time_limit=5.0,
            required=True,
            order_strict=True,
        )

        assert step.step_id == 1
        assert step.required is True

    def test_step_compliance(self):
        """Test StepCompliance dataclass."""
        step = SOPStep(
            step_id=1,
            action_id="ACT_001",
            action_name="Test",
            time_limit=5.0,
        )

        compliance = StepCompliance(
            step=step,
            status=ComplianceStatus.COMPLIANT,
            actual_time=1.0,
            time_taken=2.0,
            deviation=0.0,
            feedback="Completed on time",
        )

        assert compliance.status == ComplianceStatus.COMPLIANT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
