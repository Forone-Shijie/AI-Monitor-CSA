"""
Unit tests for video input sources.

Tests FileInput, CameraInput, RTSPInput and related classes.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.input.file_input import FileInput
from src.input.video_source import VideoFrame, VideoSourceInfo, VideoSourceType


class TestVideoFrame:
    """Tests for VideoFrame dataclass."""

    def test_video_frame_creation(self):
        """Test creating a VideoFrame."""
        data = np.zeros((480, 640, 3), dtype=np.uint8)
        frame = VideoFrame(
            data=data,
            timestamp=1.5,
            frame_number=45,
            width=640,
            height=480,
        )

        assert frame.width == 640
        assert frame.height == 480
        assert frame.timestamp == 1.5
        assert frame.frame_number == 45
        assert frame.data.shape == (480, 640, 3)


class TestVideoSourceInfo:
    """Tests for VideoSourceInfo dataclass."""

    def test_video_source_info_file(self):
        """Test VideoSourceInfo for file source."""
        info = VideoSourceInfo(
            source_type=VideoSourceType.FILE,
            width=1920,
            height=1080,
            fps=30.0,
            total_frames=9000,
            duration=300.0,
            source_path="/path/to/video.mp4",
        )

        assert info.source_type == VideoSourceType.FILE
        assert info.width == 1920
        assert info.height == 1080
        assert info.fps == 30.0
        assert info.total_frames == 9000
        assert info.duration == 300.0

    def test_video_source_info_camera(self):
        """Test VideoSourceInfo for camera source (no total frames)."""
        info = VideoSourceInfo(
            source_type=VideoSourceType.CAMERA,
            width=1280,
            height=720,
            fps=30.0,
            total_frames=None,
            duration=None,
            source_path="camera:0",
        )

        assert info.source_type == VideoSourceType.CAMERA
        assert info.total_frames is None
        assert info.duration is None


class TestFileInput:
    """Tests for FileInput class."""

    @pytest.fixture
    def mock_video_capture(self):
        """Create a mock VideoCapture for testing."""
        with patch("cv2.VideoCapture") as mock:
            # Configure mock
            instance = MagicMock()
            mock.return_value = instance

            # Mock isOpened
            instance.isOpened.return_value = True

            # Mock get for video properties
            def mock_get(prop):
                props = {
                    3: 640,  # CAP_PROP_FRAME_WIDTH
                    4: 480,  # CAP_PROP_FRAME_HEIGHT
                    5: 30.0,  # CAP_PROP_FPS
                    7: 300,  # CAP_PROP_FRAME_COUNT
                }
                return props.get(prop, 0)

            instance.get.side_effect = mock_get

            # Mock read
            frame_data = np.zeros((480, 640, 3), dtype=np.uint8)
            instance.read.return_value = (True, frame_data)

            yield mock, instance

    def test_file_not_found(self):
        """Test FileInput raises error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            FileInput("/nonexistent/path/video.mp4")

    def test_read_frame(self, mock_video_capture, tmp_path):
        """Test reading frames from FileInput."""
        # Create a temporary file to pass existence check
        test_file = tmp_path / "test.mp4"
        test_file.touch()

        mock, instance = mock_video_capture

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_file", return_value=True):
                video = FileInput(str(test_file))

                # Read a frame
                success, frame = video.read_frame()

                assert success is True
                assert frame is not None
                assert isinstance(frame, VideoFrame)
                assert frame.width == 640
                assert frame.height == 480

                video.release()

    def test_get_info(self, mock_video_capture, tmp_path):
        """Test getting video info."""
        test_file = tmp_path / "test.mp4"
        test_file.touch()

        mock, instance = mock_video_capture

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_file", return_value=True):
                video = FileInput(str(test_file))

                info = video.get_info()

                assert info.source_type == VideoSourceType.FILE
                assert info.width == 640
                assert info.height == 480
                assert info.fps == 30.0

                video.release()

    def test_context_manager(self, mock_video_capture, tmp_path):
        """Test FileInput as context manager."""
        test_file = tmp_path / "test.mp4"
        test_file.touch()

        mock, instance = mock_video_capture

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_file", return_value=True):
                with FileInput(str(test_file)) as video:
                    assert video.is_opened()

                # After context exit, should be released
                assert not video.is_opened()

    def test_seek(self, mock_video_capture, tmp_path):
        """Test seeking to a specific frame."""
        test_file = tmp_path / "test.mp4"
        test_file.touch()

        mock, instance = mock_video_capture

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_file", return_value=True):
                video = FileInput(str(test_file))

                # Seek to frame 100
                result = video.seek(100)
                assert result is True

                # Seek beyond total frames should fail
                result = video.seek(1000)
                assert result is False

                video.release()

    def test_iteration(self, mock_video_capture, tmp_path):
        """Test iterating over frames."""
        test_file = tmp_path / "test.mp4"
        test_file.touch()

        mock, instance = mock_video_capture

        # Make read return False after 3 frames
        read_count = [0]

        def mock_read():
            read_count[0] += 1
            if read_count[0] > 3:
                return (False, None)
            return (True, np.zeros((480, 640, 3), dtype=np.uint8))

        instance.read.side_effect = mock_read

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_file", return_value=True):
                video = FileInput(str(test_file))

                frames = list(video)
                assert len(frames) == 3

                video.release()


class TestCameraInput:
    """Tests for CameraInput class."""

    @pytest.fixture
    def mock_camera(self):
        """Create a mock camera for testing."""
        with patch("cv2.VideoCapture") as mock:
            instance = MagicMock()
            mock.return_value = instance

            instance.isOpened.return_value = True

            def mock_get(prop):
                props = {
                    3: 1280,  # CAP_PROP_FRAME_WIDTH
                    4: 720,  # CAP_PROP_FRAME_HEIGHT
                    5: 30.0,  # CAP_PROP_FPS
                }
                return props.get(prop, 0)

            instance.get.side_effect = mock_get

            frame_data = np.zeros((720, 1280, 3), dtype=np.uint8)
            instance.read.return_value = (True, frame_data)

            yield mock, instance

    def test_camera_open(self, mock_camera):
        """Test opening a camera."""
        from src.input.camera_input import CameraInput

        camera = CameraInput(camera_id=0)

        assert camera.is_opened()
        assert camera.get_frame_size() == (1280, 720)
        assert camera.get_fps() == 30.0

        camera.release()

    def test_camera_read_frame(self, mock_camera):
        """Test reading frame from camera."""
        from src.input.camera_input import CameraInput

        camera = CameraInput(camera_id=0)

        success, frame = camera.read_frame()

        assert success is True
        assert frame is not None
        assert frame.width == 1280
        assert frame.height == 720

        camera.release()

    def test_camera_info(self, mock_camera):
        """Test camera info."""
        from src.input.camera_input import CameraInput

        camera = CameraInput(camera_id=0)

        info = camera.get_info()

        assert info.source_type == VideoSourceType.CAMERA
        assert info.total_frames is None  # Live stream
        assert info.duration is None

        camera.release()


class TestVideoSourceType:
    """Tests for VideoSourceType enum."""

    def test_source_types(self):
        """Test video source type values."""
        assert VideoSourceType.CAMERA.value == "camera"
        assert VideoSourceType.FILE.value == "file"
        assert VideoSourceType.RTSP.value == "rtsp"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
