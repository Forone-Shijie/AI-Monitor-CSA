"""
Unit tests for pose detection module.

Tests PoseDetector, MediaPipePose and related classes.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.perception.pose_detector import (
    BodyPart,
    JointAngles,
    Landmark,
    POSE_CONNECTIONS,
    PoseResult,
    PoseType,
)


class TestLandmark:
    """Tests for Landmark dataclass."""

    def test_landmark_creation(self):
        """Test creating a Landmark."""
        lm = Landmark(x=0.5, y=0.5, z=0.0, visibility=0.95)

        assert lm.x == 0.5
        assert lm.y == 0.5
        assert lm.z == 0.0
        assert lm.visibility == 0.95

    def test_landmark_to_pixel(self):
        """Test converting normalized coords to pixel coords."""
        lm = Landmark(x=0.5, y=0.25, z=0.0, visibility=1.0)

        px, py = lm.to_pixel(width=640, height=480)

        assert px == 320  # 0.5 * 640
        assert py == 120  # 0.25 * 480

    def test_landmark_to_array(self):
        """Test converting to numpy array."""
        lm = Landmark(x=0.1, y=0.2, z=0.3, visibility=0.9)

        arr = lm.to_array()

        assert isinstance(arr, np.ndarray)
        assert len(arr) == 3
        np.testing.assert_array_almost_equal(arr, [0.1, 0.2, 0.3])


class TestJointAngles:
    """Tests for JointAngles dataclass."""

    def test_joint_angles_creation(self):
        """Test creating JointAngles."""
        angles = JointAngles(
            left_elbow=90.0,
            right_elbow=95.0,
            left_knee=170.0,
            right_knee=175.0,
            torso=5.0,
        )

        assert angles.left_elbow == 90.0
        assert angles.right_elbow == 95.0
        assert angles.left_knee == 170.0
        assert angles.torso == 5.0

    def test_joint_angles_to_dict(self):
        """Test converting to dictionary."""
        angles = JointAngles(left_elbow=90.0, right_knee=100.0)

        d = angles.to_dict()

        assert isinstance(d, dict)
        assert d["left_elbow"] == 90.0
        assert d["right_knee"] == 100.0
        assert d["left_knee"] is None  # Unset values


class TestPoseResult:
    """Tests for PoseResult dataclass."""

    @pytest.fixture
    def sample_landmarks(self):
        """Create sample landmarks (33 points)."""
        return [
            Landmark(x=i * 0.03, y=i * 0.03, z=0.0, visibility=0.9)
            for i in range(33)
        ]

    def test_pose_result_detected(self, sample_landmarks):
        """Test PoseResult with detected pose."""
        result = PoseResult(
            detected=True,
            confidence=0.85,
            landmarks=sample_landmarks,
            pose_type=PoseType.STANDING,
            timestamp=1.0,
            frame_number=30,
        )

        assert result.detected is True
        assert result.confidence == 0.85
        assert len(result.landmarks) == 33
        assert result.pose_type == PoseType.STANDING

    def test_pose_result_not_detected(self):
        """Test PoseResult when no pose detected."""
        result = PoseResult(
            detected=False,
            confidence=0.0,
        )

        assert result.detected is False
        assert result.confidence == 0.0
        assert len(result.landmarks) == 0

    def test_get_landmark(self, sample_landmarks):
        """Test getting landmark by body part."""
        result = PoseResult(
            detected=True,
            confidence=0.9,
            landmarks=sample_landmarks,
        )

        nose = result.get_landmark(BodyPart.NOSE)
        assert nose is not None
        assert nose.x == 0.0  # First landmark

        left_shoulder = result.get_landmark(BodyPart.LEFT_SHOULDER)
        assert left_shoulder is not None
        assert left_shoulder.x == 11 * 0.03  # Index 11

    def test_get_landmarks_array(self, sample_landmarks):
        """Test getting landmarks as numpy array."""
        result = PoseResult(
            detected=True,
            confidence=0.9,
            landmarks=sample_landmarks,
        )

        arr = result.get_landmarks_array()

        assert isinstance(arr, np.ndarray)
        assert arr.shape == (33, 3)

    def test_get_visibility_array(self, sample_landmarks):
        """Test getting visibility scores."""
        result = PoseResult(
            detected=True,
            confidence=0.9,
            landmarks=sample_landmarks,
        )

        vis = result.get_visibility_array()

        assert isinstance(vis, np.ndarray)
        assert len(vis) == 33
        assert all(v == 0.9 for v in vis)


class TestPoseType:
    """Tests for PoseType enum."""

    def test_pose_type_values(self):
        """Test pose type values."""
        assert PoseType.UNKNOWN.value == "unknown"
        assert PoseType.STANDING.value == "standing"
        assert PoseType.SITTING.value == "sitting"
        assert PoseType.SQUATTING.value == "squatting"
        assert PoseType.BENDING.value == "bending"
        assert PoseType.BRACE_POSITION.value == "brace_position"


class TestBodyPart:
    """Tests for BodyPart enum."""

    def test_body_part_values(self):
        """Test body part index values."""
        assert BodyPart.NOSE.value == 0
        assert BodyPart.LEFT_SHOULDER.value == 11
        assert BodyPart.RIGHT_SHOULDER.value == 12
        assert BodyPart.LEFT_HIP.value == 23
        assert BodyPart.RIGHT_HIP.value == 24
        assert BodyPart.LEFT_KNEE.value == 25
        assert BodyPart.RIGHT_ANKLE.value == 28

    def test_body_part_count(self):
        """Test total number of body parts."""
        # MediaPipe has 33 landmarks
        assert len(BodyPart) == 33


class TestPoseConnections:
    """Tests for pose connections."""

    def test_pose_connections_exist(self):
        """Test that pose connections are defined."""
        assert len(POSE_CONNECTIONS) > 0

    def test_pose_connections_valid(self):
        """Test that all connections reference valid body parts."""
        for start, end in POSE_CONNECTIONS:
            assert isinstance(start, BodyPart)
            assert isinstance(end, BodyPart)
            assert start.value < 33
            assert end.value < 33


class TestMediaPipePose:
    """Tests for MediaPipePose class."""

    @pytest.fixture
    def mock_mediapipe(self):
        """Create mock MediaPipe module."""
        with patch.dict("sys.modules", {"mediapipe": MagicMock()}):
            import sys

            mp = sys.modules["mediapipe"]

            # Mock solutions.pose
            mock_pose_class = MagicMock()
            mp.solutions.pose = MagicMock()
            mp.solutions.pose.Pose = mock_pose_class
            mp.solutions.drawing_utils = MagicMock()

            # Create mock pose instance
            mock_pose = MagicMock()
            mock_pose_class.return_value = mock_pose

            # Mock landmarks result
            mock_landmarks = MagicMock()
            mock_landmarks.landmark = [
                MagicMock(x=i * 0.03, y=i * 0.03, z=0.0, visibility=0.9)
                for i in range(33)
            ]

            mock_result = MagicMock()
            mock_result.pose_landmarks = mock_landmarks
            mock_pose.process.return_value = mock_result

            yield mp, mock_pose

    def test_mediapipe_init(self, mock_mediapipe):
        """Test MediaPipePose initialization."""
        from src.perception.mediapipe_pose import MediaPipePose

        detector = MediaPipePose(model_complexity=1)

        assert detector.is_initialized
        assert detector.model_complexity == 1

    def test_mediapipe_detect(self, mock_mediapipe):
        """Test pose detection."""
        from src.perception.mediapipe_pose import MediaPipePose

        detector = MediaPipePose()

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        result = detector.detect(frame)

        assert result.detected is True
        assert len(result.landmarks) == 33
        assert result.angles is not None

    def test_mediapipe_no_detection(self, mock_mediapipe):
        """Test when no pose is detected."""
        from src.perception.mediapipe_pose import MediaPipePose

        mp, mock_pose = mock_mediapipe

        # Configure mock to return no landmarks
        mock_result = MagicMock()
        mock_result.pose_landmarks = None
        mock_pose.process.return_value = mock_result

        detector = MediaPipePose()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        result = detector.detect(frame)

        assert result.detected is False
        assert len(result.landmarks) == 0

    def test_mediapipe_context_manager(self, mock_mediapipe):
        """Test MediaPipePose as context manager."""
        from src.perception.mediapipe_pose import MediaPipePose

        with MediaPipePose() as detector:
            assert detector.is_initialized

        # After exit, should be released
        assert not detector.is_initialized

    def test_mediapipe_release(self, mock_mediapipe):
        """Test releasing resources."""
        from src.perception.mediapipe_pose import MediaPipePose

        detector = MediaPipePose()
        assert detector.is_initialized

        detector.release()

        assert not detector.is_initialized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
