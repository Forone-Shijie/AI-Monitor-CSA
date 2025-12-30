"""
Unit tests for pose detection module.

Tests PoseDetector, RTMPoseDetector and related classes.
Uses COCO 17-point keypoint format.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.perception.pose_detector import (
    BodyPart,
    JointAngles,
    Landmark,
    NUM_KEYPOINTS,
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
        """Create sample landmarks (17 points for COCO format)."""
        return [
            Landmark(x=i * 0.05, y=i * 0.05, z=0.0, visibility=0.9)
            for i in range(NUM_KEYPOINTS)
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
        assert len(result.landmarks) == NUM_KEYPOINTS
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
        """Test getting landmark by body part (COCO 17-point format)."""
        result = PoseResult(
            detected=True,
            confidence=0.9,
            landmarks=sample_landmarks,
        )

        nose = result.get_landmark(BodyPart.NOSE)
        assert nose is not None
        assert nose.x == 0.0  # Index 0

        # LEFT_SHOULDER is index 5 in COCO format
        left_shoulder = result.get_landmark(BodyPart.LEFT_SHOULDER)
        assert left_shoulder is not None
        assert left_shoulder.x == 5 * 0.05

        # LEFT_HIP is index 11 in COCO format
        left_hip = result.get_landmark(BodyPart.LEFT_HIP)
        assert left_hip is not None
        assert left_hip.x == 11 * 0.05

    def test_get_landmarks_array(self, sample_landmarks):
        """Test getting landmarks as numpy array."""
        result = PoseResult(
            detected=True,
            confidence=0.9,
            landmarks=sample_landmarks,
        )

        arr = result.get_landmarks_array()

        assert isinstance(arr, np.ndarray)
        assert arr.shape == (NUM_KEYPOINTS, 3)

    def test_get_visibility_array(self, sample_landmarks):
        """Test getting visibility scores."""
        result = PoseResult(
            detected=True,
            confidence=0.9,
            landmarks=sample_landmarks,
        )

        vis = result.get_visibility_array()

        assert isinstance(vis, np.ndarray)
        assert len(vis) == NUM_KEYPOINTS
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
    """Tests for BodyPart enum (COCO 17-point format)."""

    def test_body_part_values(self):
        """Test body part index values (COCO 17-point)."""
        # Head
        assert BodyPart.NOSE.value == 0
        assert BodyPart.LEFT_EYE.value == 1
        assert BodyPart.RIGHT_EYE.value == 2
        assert BodyPart.LEFT_EAR.value == 3
        assert BodyPart.RIGHT_EAR.value == 4

        # Upper body
        assert BodyPart.LEFT_SHOULDER.value == 5
        assert BodyPart.RIGHT_SHOULDER.value == 6
        assert BodyPart.LEFT_ELBOW.value == 7
        assert BodyPart.RIGHT_ELBOW.value == 8
        assert BodyPart.LEFT_WRIST.value == 9
        assert BodyPart.RIGHT_WRIST.value == 10

        # Lower body
        assert BodyPart.LEFT_HIP.value == 11
        assert BodyPart.RIGHT_HIP.value == 12
        assert BodyPart.LEFT_KNEE.value == 13
        assert BodyPart.RIGHT_KNEE.value == 14
        assert BodyPart.LEFT_ANKLE.value == 15
        assert BodyPart.RIGHT_ANKLE.value == 16

    def test_body_part_count(self):
        """Test total number of body parts (COCO 17)."""
        assert len(BodyPart) == NUM_KEYPOINTS
        assert NUM_KEYPOINTS == 17


class TestPoseConnections:
    """Tests for pose connections (COCO 17-point format)."""

    def test_pose_connections_exist(self):
        """Test that pose connections are defined."""
        assert len(POSE_CONNECTIONS) > 0

    def test_pose_connections_valid(self):
        """Test that all connections reference valid body parts."""
        for start, end in POSE_CONNECTIONS:
            assert isinstance(start, BodyPart)
            assert isinstance(end, BodyPart)
            assert start.value < NUM_KEYPOINTS
            assert end.value < NUM_KEYPOINTS

    def test_pose_connections_count(self):
        """Test expected number of connections for COCO 17-point."""
        # COCO skeleton has 16 connections
        assert len(POSE_CONNECTIONS) == 16


class TestRTMPoseDetector:
    """Tests for RTMPoseDetector class."""

    @pytest.fixture
    def mock_mmpose(self):
        """Create mock MMPose modules."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        mock_mmdet = MagicMock()
        mock_mmpose = MagicMock()

        # Mock detector
        mock_detector = MagicMock()
        mock_mmdet.apis.init_detector.return_value = mock_detector

        # Mock pose estimator
        mock_pose_estimator = MagicMock()
        mock_mmpose.apis.init_model.return_value = mock_pose_estimator

        # Mock detection result
        mock_det_result = MagicMock()
        mock_pred_instances = MagicMock()
        mock_pred_instances.bboxes = MagicMock()
        mock_pred_instances.bboxes.cpu.return_value.numpy.return_value = np.array(
            [[100, 100, 200, 400]]
        )
        mock_pred_instances.scores = MagicMock()
        mock_pred_instances.scores.cpu.return_value.numpy.return_value = np.array(
            [0.9]
        )
        mock_pred_instances.labels = MagicMock()
        mock_pred_instances.labels.cpu.return_value.numpy.return_value = np.array([0])
        mock_det_result.pred_instances = mock_pred_instances
        mock_mmdet.apis.inference_detector.return_value = mock_det_result

        # Mock pose result
        mock_pose_result = MagicMock()
        mock_pose_instances = MagicMock()
        mock_pose_instances.keypoints = np.array(
            [[[i * 10, i * 10] for i in range(17)]]
        )
        mock_pose_instances.keypoint_scores = np.array([[0.9] * 17])
        mock_pose_result.pred_instances = mock_pose_instances
        mock_mmpose.apis.inference_topdown.return_value = [mock_pose_result]

        with patch.dict(
            "sys.modules",
            {
                "torch": mock_torch,
                "mmdet": mock_mmdet,
                "mmdet.apis": mock_mmdet.apis,
                "mmpose": mock_mmpose,
                "mmpose.apis": mock_mmpose.apis,
            },
        ):
            yield mock_torch, mock_mmdet, mock_mmpose

    def test_rtmpose_initialization(self):
        """Test RTMPoseDetector initializes successfully with MMPose installed."""
        try:
            from src.perception.rtmpose_detector import RTMPoseDetector

            detector = RTMPoseDetector(device="cpu")
            assert detector._is_initialized is True
            detector.release()
        except ImportError:
            pytest.skip("MMPose not installed")


class TestNumKeypoints:
    """Tests for NUM_KEYPOINTS constant."""

    def test_num_keypoints_value(self):
        """Test NUM_KEYPOINTS is 17 (COCO format)."""
        assert NUM_KEYPOINTS == 17

    def test_num_keypoints_matches_body_part_count(self):
        """Test NUM_KEYPOINTS matches BodyPart enum count."""
        assert NUM_KEYPOINTS == len(BodyPart)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
