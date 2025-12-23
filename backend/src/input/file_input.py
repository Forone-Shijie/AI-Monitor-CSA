"""
File Input - Video file reader implementation.

Reads video frames from local video files (mp4, avi, etc.).
"""

import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from .video_source import VideoFrame, VideoSource, VideoSourceInfo, VideoSourceType


class FileInput(VideoSource):
    """
    Video file input source.

    Reads frames from local video files using OpenCV.

    Supported formats: mp4, avi, mkv, mov, webm, and other formats
    supported by the installed OpenCV/FFmpeg.

    Usage:
        with FileInput("video.mp4") as video:
            for frame in video:
                # Process frame.data (numpy array in BGR format)
                pass

        # Or manually:
        video = FileInput("video.mp4")
        while video.is_opened():
            success, frame = video.read_frame()
            if not success:
                break
        video.release()
    """

    def __init__(
        self,
        file_path: str,
        loop: bool = False,
        start_frame: int = 0,
    ) -> None:
        """
        Initialize file input.

        Args:
            file_path: Path to the video file
            loop: If True, loop back to start when reaching end
            start_frame: Frame number to start reading from
        """
        super().__init__()

        self._file_path = Path(file_path)
        self._loop = loop
        self._start_frame = start_frame

        # Validate file exists
        if not self._file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        if not self._file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Open video capture
        self._cap = cv2.VideoCapture(str(self._file_path))

        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {file_path}")

        # Get video properties
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._duration = self._total_frames / self._fps if self._fps > 0 else 0

        # Seek to start frame if specified
        if start_frame > 0:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            self._frame_count = start_frame

        self._is_opened = True
        self._start_time = time.time()

    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        """
        Read a single frame from the video file.

        Returns:
            Tuple of (success, VideoFrame or None)
        """
        if not self._is_opened or not self._cap.isOpened():
            return False, None

        ret, frame_data = self._cap.read()

        if not ret:
            if self._loop:
                # Loop back to start
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._start_frame)
                self._frame_count = self._start_frame
                ret, frame_data = self._cap.read()
                if not ret:
                    return False, None
            else:
                self._is_opened = False
                return False, None

        # Calculate timestamp
        timestamp = self._frame_count / self._fps if self._fps > 0 else 0

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
        """Get video frame rate."""
        return self._fps

    def get_frame_size(self) -> Tuple[int, int]:
        """Get frame dimensions (width, height)."""
        return self._width, self._height

    def release(self) -> None:
        """Release video capture resources."""
        if self._cap is not None:
            self._cap.release()
        self._is_opened = False

    def is_opened(self) -> bool:
        """Check if video file is open."""
        return self._is_opened and self._cap.isOpened()

    def get_info(self) -> VideoSourceInfo:
        """Get video source information."""
        return VideoSourceInfo(
            source_type=VideoSourceType.FILE,
            width=self._width,
            height=self._height,
            fps=self._fps,
            total_frames=self._total_frames,
            duration=self._duration,
            source_path=str(self._file_path),
        )

    def seek(self, frame_number: int) -> bool:
        """
        Seek to a specific frame.

        Args:
            frame_number: Target frame number

        Returns:
            True if seek successful
        """
        if not self._is_opened:
            return False

        if frame_number < 0 or frame_number >= self._total_frames:
            return False

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._frame_count = frame_number
        return True

    def get_total_frames(self) -> int:
        """Get total number of frames in the video."""
        return self._total_frames

    def get_duration(self) -> float:
        """Get video duration in seconds."""
        return self._duration

    def get_current_position(self) -> float:
        """Get current position in seconds."""
        return self._frame_count / self._fps if self._fps > 0 else 0

    def set_position(self, seconds: float) -> bool:
        """
        Set position by time in seconds.

        Args:
            seconds: Target position in seconds

        Returns:
            True if successful
        """
        if self._fps <= 0:
            return False

        frame_number = int(seconds * self._fps)
        return self.seek(frame_number)

    @property
    def file_path(self) -> Path:
        """Get the video file path."""
        return self._file_path
