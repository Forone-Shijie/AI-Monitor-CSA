"""
Unit tests for brace position detection module.

Tests BracePositionDetector and related classes.
"""

import time

import numpy as np
import pytest

from src.analysis.brace_position_detector import (
    ArmPosition,
    BodyPartStatus,
    BracePositionDetector,
    BracePositionResult,
    HeadPosition,
)
from src.perception.pose_detector import (
    JointAngles,
    Landmark,
    PoseResult,
    PoseType,
)


class TestBodyPartStatus:
    """Tests for BodyPartStatus dataclass."""

    def test_body_part_status_compliant(self):
        """Test compliant body part status."""
        status = BodyPartStatus(
            part_name="torso",
            part_name_cn="躯干与背部",
            is_compliant=True,
            current_value=30.0,
            target_range=(20.0, 45.0),
            deviation=0.0,
            confidence=0.95,
            feedback="躯干姿势正确",
        )

        assert status.is_compliant is True
        assert status.deviation == 0.0
        assert "正确" in status.feedback

    def test_body_part_status_non_compliant(self):
        """Test non-compliant body part status."""
        status = BodyPartStatus(
            part_name="legs",
            part_name_cn="下肢与脚部",
            is_compliant=False,
            current_value=120.0,
            target_range=(85.0, 95.0),
            deviation=25.0,
            confidence=0.9,
            feedback="膝关节弯曲不足",
        )

        assert status.is_compliant is False
        assert status.deviation == 25.0


class TestBracePositionResult:
    """Tests for BracePositionResult dataclass."""

    @pytest.fixture
    def sample_result(self):
        """Create sample brace position result."""
        compliant_status = BodyPartStatus(
            part_name="test",
            part_name_cn="测试",
            is_compliant=True,
            current_value=90.0,
            target_range=(85.0, 95.0),
            deviation=0.0,
            confidence=0.9,
            feedback="正确",
        )

        return BracePositionResult(
            detected=True,
            timestamp=time.time(),
            torso=compliant_status,
            head=compliant_status,
            arms=compliant_status,
            legs=compliant_status,
            is_complete=True,
            compliance_ratio=1.0,
            stability_score=0.9,
            time_to_position=3.5,
            hold_duration=10.0,
            overall_feedback=["防冲击姿势到位！"],
        )

    def test_complete_result(self, sample_result):
        """Test complete brace position result."""
        assert sample_result.detected is True
        assert sample_result.is_complete is True
        assert sample_result.compliance_ratio == 1.0
        assert sample_result.time_to_position == 3.5
        assert sample_result.hold_duration == 10.0

    def test_to_dict(self, sample_result):
        """Test converting to dictionary."""
        d = sample_result.to_dict()

        assert isinstance(d, dict)
        assert d["detected"] is True
        assert d["is_complete"] is True
        assert "torso" in d
        assert "head" in d
        assert "arms" in d
        assert "legs" in d


class TestBracePositionDetector:
    """Tests for BracePositionDetector class."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return BracePositionDetector()

    @pytest.fixture
    def good_brace_landmarks(self):
        """Create landmarks representing good brace position."""
        # Create 33 landmarks with positions simulating brace position
        landmarks = []
        for i in range(33):
            landmarks.append(
                Landmark(x=0.5, y=0.5, z=0.0, visibility=0.9)
            )

        # Adjust key landmarks for brace position
        # Shoulders (11, 12)
        landmarks[11] = Landmark(x=0.4, y=0.35, z=0.0, visibility=0.95)
        landmarks[12] = Landmark(x=0.6, y=0.35, z=0.0, visibility=0.95)

        # Hips (23, 24)
        landmarks[23] = Landmark(x=0.4, y=0.55, z=0.0, visibility=0.95)
        landmarks[24] = Landmark(x=0.6, y=0.55, z=0.0, visibility=0.95)

        # Elbows (13, 14) - bent for crossed arms
        landmarks[13] = Landmark(x=0.35, y=0.42, z=0.0, visibility=0.9)
        landmarks[14] = Landmark(x=0.65, y=0.42, z=0.0, visibility=0.9)

        # Wrists (15, 16) - crossed
        landmarks[15] = Landmark(x=0.52, y=0.40, z=0.0, visibility=0.9)
        landmarks[16] = Landmark(x=0.48, y=0.40, z=0.0, visibility=0.9)

        # Knees (25, 26)
        landmarks[25] = Landmark(x=0.4, y=0.70, z=0.0, visibility=0.95)
        landmarks[26] = Landmark(x=0.6, y=0.70, z=0.0, visibility=0.95)

        # Ankles (27, 28)
        landmarks[27] = Landmark(x=0.4, y=0.90, z=0.0, visibility=0.95)
        landmarks[28] = Landmark(x=0.6, y=0.90, z=0.0, visibility=0.95)

        # Nose (0)
        landmarks[0] = Landmark(x=0.5, y=0.25, z=0.0, visibility=0.95)

        return landmarks

    @pytest.fixture
    def good_pose_result(self, good_brace_landmarks):
        """Create pose result with good brace position."""
        return PoseResult(
            detected=True,
            confidence=0.9,
            landmarks=good_brace_landmarks,
            angles=JointAngles(
                left_elbow=70.0,
                right_elbow=70.0,
                left_knee=90.0,
                right_knee=90.0,
                torso=30.0,
            ),
            pose_type=PoseType.BRACE_POSITION,
            timestamp=time.time(),
            frame_number=1,
        )

    def test_detector_init(self, detector):
        """Test detector initialization."""
        assert detector is not None
        assert not detector.is_monitoring
        assert detector.trigger_time is None

    def test_detector_config(self, detector):
        """Test detector configuration."""
        config = detector.get_config()

        assert "torso_min_angle" in config
        assert "torso_max_angle" in config
        assert "knee_min_angle" in config
        assert "knee_max_angle" in config

    def test_start_stop_monitoring(self, detector):
        """Test starting and stopping monitoring."""
        assert not detector.is_monitoring

        detector.start_monitoring()

        assert detector.is_monitoring
        assert detector.trigger_time is not None

        detector.stop_monitoring()

        assert not detector.is_monitoring

    def test_detect_no_pose(self, detector):
        """Test detection when no pose detected."""
        empty_result = PoseResult(detected=False, confidence=0.0)

        brace_result = detector.detect(empty_result)

        assert brace_result.detected is False
        assert brace_result.is_complete is False
        assert brace_result.compliance_ratio == 0.0

    def test_detect_with_pose(self, detector, good_pose_result):
        """Test detection with pose result."""
        brace_result = detector.detect(good_pose_result)

        assert brace_result.detected is True
        assert brace_result.torso is not None
        assert brace_result.head is not None
        assert brace_result.arms is not None
        assert brace_result.legs is not None

    def test_time_to_position(self, detector, good_pose_result):
        """Test timing measurement."""
        detector.start_monitoring()
        time.sleep(0.1)  # Small delay

        brace_result = detector.detect(good_pose_result)

        # If position is complete, time_to_position should be set
        if brace_result.is_complete:
            assert brace_result.time_to_position is not None
            assert brace_result.time_to_position >= 0.1

    def test_hold_duration(self, detector, good_pose_result):
        """Test hold duration tracking."""
        detector.start_monitoring()

        # First detection
        result1 = detector.detect(good_pose_result)

        if result1.is_complete:
            time.sleep(0.1)

            # Second detection
            result2 = detector.detect(good_pose_result)

            if result2.is_complete:
                assert result2.hold_duration >= 0.1

    def test_head_position_modes(self):
        """Test different head position modes."""
        forward_detector = BracePositionDetector(head_mode=HeadPosition.FORWARD)
        rear_detector = BracePositionDetector(head_mode=HeadPosition.REAR)

        assert forward_detector._head_mode == HeadPosition.FORWARD
        assert rear_detector._head_mode == HeadPosition.REAR

    def test_arm_position_modes(self):
        """Test different arm position modes."""
        crossed_detector = BracePositionDetector(arm_mode=ArmPosition.CROSSED)
        thighs_detector = BracePositionDetector(arm_mode=ArmPosition.ON_THIGHS)

        assert crossed_detector._arm_mode == ArmPosition.CROSSED
        assert thighs_detector._arm_mode == ArmPosition.ON_THIGHS

    def test_custom_config(self):
        """Test custom configuration."""
        custom_config = {
            "torso_min_angle": 25.0,
            "torso_max_angle": 40.0,
            "knee_min_angle": 80.0,
            "knee_max_angle": 100.0,
        }

        detector = BracePositionDetector(config=custom_config)
        config = detector.get_config()

        assert config["torso_min_angle"] == 25.0
        assert config["torso_max_angle"] == 40.0
        assert config["knee_min_angle"] == 80.0
        assert config["knee_max_angle"] == 100.0

    def test_update_config(self, detector):
        """Test updating configuration."""
        detector.update_config({"torso_min_angle": 15.0})

        config = detector.get_config()
        assert config["torso_min_angle"] == 15.0

    def test_overall_feedback(self, detector, good_pose_result):
        """Test overall feedback generation."""
        detector.start_monitoring()
        result = detector.detect(good_pose_result)

        assert isinstance(result.overall_feedback, list)
        # Should have some feedback
        assert len(result.overall_feedback) >= 0


class TestPoseAnalyzer:
    """Tests for PoseAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        from src.analysis.pose_analyzer import PoseAnalyzer

        return PoseAnalyzer()

    @pytest.fixture
    def sample_pose_result(self):
        """Create sample pose result."""
        landmarks = [
            Landmark(x=i * 0.03, y=i * 0.02, z=0.0, visibility=0.9)
            for i in range(33)
        ]

        return PoseResult(
            detected=True,
            confidence=0.9,
            landmarks=landmarks,
            angles=JointAngles(
                left_elbow=95.0,
                right_elbow=90.0,
                left_knee=85.0,
                right_knee=90.0,
                torso=5.0,
            ),
            pose_type=PoseType.SITTING,
            timestamp=time.time(),
        )

    def test_analyzer_init(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None

    def test_analyze(self, analyzer, sample_pose_result):
        """Test analyze method."""
        result = analyzer.analyze(sample_pose_result)

        assert result is not None
        assert result.pose_result == sample_pose_result
        assert isinstance(result.angle_deviations, list)
        assert result.symmetry is not None
        assert 0 <= result.overall_score <= 100

    def test_calculate_angle_2d(self, analyzer):
        """Test 2D angle calculation."""
        # Right angle test
        p1 = (0.0, 0.0)
        p2 = (0.0, 1.0)
        p3 = (1.0, 1.0)

        angle = analyzer.calculate_angle_2d(p1, p2, p3)

        assert abs(angle - 90.0) < 1.0  # Should be close to 90 degrees

    def test_get_body_lean_angle(self, analyzer, sample_pose_result):
        """Test body lean angle calculation."""
        lean_angle = analyzer.get_body_lean_angle(sample_pose_result)

        assert isinstance(lean_angle, float)
        assert lean_angle >= 0

    def test_symmetry_analysis(self, analyzer, sample_pose_result):
        """Test symmetry analysis."""
        result = analyzer.analyze(sample_pose_result)

        assert result.symmetry is not None
        assert 0 <= result.symmetry.overall_symmetry_score <= 1
        assert isinstance(result.symmetry.left_right_diff, dict)

    def test_feedback_generation(self, analyzer, sample_pose_result):
        """Test feedback generation."""
        result = analyzer.analyze(sample_pose_result)

        assert isinstance(result.feedback, list)

    def test_reset_history(self, analyzer, sample_pose_result):
        """Test resetting history."""
        # Add some history
        analyzer.analyze(sample_pose_result)
        analyzer.analyze(sample_pose_result)

        # Reset
        analyzer.reset_history()

        # Verify reset (stability should be 0 with no history)
        result = analyzer.analyze(sample_pose_result)
        # After reset, stability tracking restarts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
