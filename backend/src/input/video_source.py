"""
Video Source Abstract Base Class

Defines the interface for all video input sources in CC-SOP Monitor.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

import numpy as np


class VideoSourceType(Enum):
    """Video source type enumeration."""

    CAMERA = "camera"
    FILE = "file"
    RTSP = "rtsp"


@dataclass
class VideoFrame:
    """Video frame data container."""

    data: np.ndarray  # BGR format, shape: (height, width, 3)
    timestamp: float  # Frame timestamp in seconds
    frame_number: int  # Frame index
    width: int
    height: int


@dataclass
class VideoSourceInfo:
    """Video source information."""

    source_type: VideoSourceType
    width: int
    height: int
    fps: float
    total_frames: Optional[int] = None  # None for live streams
    duration: Optional[float] = None  # None for live streams
    source_path: Optional[str] = None


class VideoSource(ABC):
    """
    Abstract base class for video sources.

    All video input implementations must inherit from this class
    and implement the abstract methods.

    Usage:
        source = FileInput("video.mp4")
        while source.is_opened():
            success, frame = source.read_frame()
            if not success:
                break
            # Process frame...
        source.release()
    """

    def __init__(self) -> None:
        self._frame_count: int = 0
        self._is_opened: bool = False

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        """
        Read a single frame from the video source.

        Returns:
            Tuple of (success: bool, frame: Optional[VideoFrame])
            - success: True if frame was read successfully
            - frame: VideoFrame object or None if read failed
        """
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """
        Get the frame rate of the video source.

        Returns:
            Frame rate in frames per second
        """
        pass

    @abstractmethod
    def get_frame_size(self) -> Tuple[int, int]:
        """
        Get the frame dimensions.

        Returns:
            Tuple of (width, height)
        """
        pass

    @abstractmethod
    def release(self) -> None:
        """
        Release the video source and free resources.

        Should be called when done using the video source.
        """
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """
        Check if the video source is currently open and available.

        Returns:
            True if source is open and ready for reading
        """
        pass

    @abstractmethod
    def get_info(self) -> VideoSourceInfo:
        """
        Get detailed information about the video source.

        Returns:
            VideoSourceInfo object with source details
        """
        pass

    def get_frame_count(self) -> int:
        """
        Get the number of frames read so far.

        Returns:
            Number of frames read
        """
        return self._frame_count

    def seek(self, frame_number: int) -> bool:
        """
        Seek to a specific frame (optional, may not be supported by all sources).

        Args:
            frame_number: Frame index to seek to

        Returns:
            True if seek was successful, False otherwise
        """
        return False  # Default: seeking not supported

    def __enter__(self) -> "VideoSource":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Context manager exit - ensures resources are released."""
        self.release()

    def __iter__(self) -> "VideoSource":
        """Make video source iterable."""
        return self

    def __next__(self) -> VideoFrame:
        """Get next frame for iteration."""
        success, frame = self.read_frame()
        if not success or frame is None:
            raise StopIteration
        return frame
