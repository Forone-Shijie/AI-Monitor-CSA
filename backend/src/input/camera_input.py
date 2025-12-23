"""
Camera Input - Local camera/webcam reader implementation.

Captures video frames from local cameras (webcam, USB cameras, etc.).
"""

import time
from typing import Optional, Tuple

import cv2

from .video_source import VideoFrame, VideoSource, VideoSourceInfo, VideoSourceType


class CameraInput(VideoSource):
    """
    Local camera input source.

    Captures frames from local cameras using OpenCV.

    Usage:
        with CameraInput(camera_id=0) as camera:
            for frame in camera:
                # Process frame.data (numpy array in BGR format)
                pass

        # With custom resolution:
        camera = CameraInput(camera_id=0, width=1920, height=1080, fps=30)
    """

    def __init__(
        self,
        camera_id: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        backend: int = cv2.CAP_ANY,
    ) -> None:
        """
        Initialize camera input.

        Args:
            camera_id: Camera device ID (0 for default camera)
            width: Desired frame width (None for default)
            height: Desired frame height (None for default)
            fps: Desired frame rate (None for default)
            backend: OpenCV capture backend (cv2.CAP_ANY, cv2.CAP_V4L2, etc.)
        """
        super().__init__()

        self._camera_id = camera_id
        self._requested_width = width
        self._requested_height = height
        self._requested_fps = fps

        # Open camera
        self._cap = cv2.VideoCapture(camera_id, backend)

        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open camera {camera_id}")

        # Set resolution if specified
        if width is not None:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height is not None:
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fps is not None:
            self._cap.set(cv2.CAP_PROP_FPS, fps)

        # Get actual properties (may differ from requested)
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)

        # Handle case where FPS is 0 or invalid
        if self._fps <= 0:
            self._fps = 30.0  # Default assumption

        self._is_opened = True
        self._start_time = time.time()

    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        """
        Read a single frame from the camera.

        Returns:
            Tuple of (success, VideoFrame or None)
        """
        if not self._is_opened or not self._cap.isOpened():
            return False, None

        ret, frame_data = self._cap.read()

        if not ret:
            return False, None

        # Calculate timestamp from start
        timestamp = time.time() - self._start_time

        frame = VideoFrame(
            data=frame_data,
            timestamp=timestamp,
            frame_number=self._frame_count,
            width=self._width,
            height=self._height,
        )

        self._frame_count += 1
        return True, frame

    def get_fps(self) -> float:
        """Get camera frame rate."""
        return self._fps

    def get_frame_size(self) -> Tuple[int, int]:
        """Get frame dimensions (width, height)."""
        return self._width, self._height

    def release(self) -> None:
        """Release camera resources."""
        if self._cap is not None:
            self._cap.release()
        self._is_opened = False

    def is_opened(self) -> bool:
        """Check if camera is open."""
        return self._is_opened and self._cap.isOpened()

    def get_info(self) -> VideoSourceInfo:
        """Get camera source information."""
        return VideoSourceInfo(
            source_type=VideoSourceType.CAMERA,
            width=self._width,
            height=self._height,
            fps=self._fps,
            total_frames=None,  # Live stream, unknown total
            duration=None,  # Live stream, no duration
            source_path=f"camera:{self._camera_id}",
        )

    def set_resolution(self, width: int, height: int) -> bool:
        """
        Set camera resolution.

        Args:
            width: Desired width
            height: Desired height

        Returns:
            True if successful (actual resolution may differ)
        """
        if not self._is_opened:
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # Update actual values
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        return True

    def set_fps(self, fps: float) -> bool:
        """
        Set camera frame rate.

        Args:
            fps: Desired frame rate

        Returns:
            True if successful (actual FPS may differ)
        """
        if not self._is_opened:
            return False

        self._cap.set(cv2.CAP_PROP_FPS, fps)
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)

        if self._fps <= 0:
            self._fps = fps  # Use requested value if read fails

        return True

    def set_autofocus(self, enabled: bool) -> bool:
        """
        Enable or disable autofocus.

        Args:
            enabled: True to enable autofocus

        Returns:
            True if successful
        """
        if not self._is_opened:
            return False

        return self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 1 if enabled else 0)

    def set_exposure(self, exposure: float) -> bool:
        """
        Set camera exposure.

        Args:
            exposure: Exposure value

        Returns:
            True if successful
        """
        if not self._is_opened:
            return False

        return self._cap.set(cv2.CAP_PROP_EXPOSURE, exposure)

    @property
    def camera_id(self) -> int:
        """Get camera device ID."""
        return self._camera_id

    @staticmethod
    def list_cameras(max_cameras: int = 10) -> list[int]:
        """
        List available camera IDs.

        Args:
            max_cameras: Maximum number of cameras to check

        Returns:
            List of available camera IDs
        """
        available = []
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
