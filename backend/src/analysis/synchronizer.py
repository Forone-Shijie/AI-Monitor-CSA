"""
Synchronizer - Multi-modal data alignment and synchronization.

Aligns data from different sources (video, audio, events) by timestamp
to enable unified analysis.
"""

import bisect
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar

import numpy as np


class DataType(Enum):
    """Types of data that can be synchronized."""

    POSE = "pose"  # Pose detection results
    ACTION = "action"  # Action recognition events
    ASR = "asr"  # Speech recognition results
    EVENT = "event"  # System events
    FRAME = "frame"  # Video frames


T = TypeVar("T")


@dataclass
class TimestampedData(Generic[T]):
    """A piece of data with timestamp."""

    timestamp: float  # Unix timestamp
    data: T  # The actual data
    data_type: DataType
    source: str = "default"  # Data source identifier
    confidence: float = 1.0


@dataclass
class SyncedFrame:
    """A synchronized frame containing aligned multi-modal data."""

    timestamp: float
    frame_number: int

    # Data from different modalities
    pose: Optional[Any] = None
    action: Optional[Any] = None
    asr_text: Optional[str] = None
    events: List[Any] = field(default_factory=list)

    # Metadata
    has_pose: bool = False
    has_action: bool = False
    has_asr: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "frame_number": self.frame_number,
            "has_pose": self.has_pose,
            "has_action": self.has_action,
            "has_asr": self.has_asr,
            "asr_text": self.asr_text,
            "events": [str(e) for e in self.events],
        }


class Synchronizer:
    """
    Multi-modal data synchronizer.

    Collects data from multiple sources and aligns them by timestamp
    for unified analysis.

    Usage:
        sync = Synchronizer(tolerance=0.1)  # 100ms tolerance

        # Add data from different sources
        sync.add_pose(timestamp=1.0, pose_result=pose)
        sync.add_asr(timestamp=1.05, asr_result=asr)
        sync.add_action(timestamp=1.1, action_event=action)

        # Get synchronized data at a specific time
        frame = sync.get_synced_frame(timestamp=1.0)
        print(f"Pose: {frame.has_pose}, ASR: {frame.asr_text}")

        # Or get a time range
        frames = sync.get_frames_in_range(start=0.0, end=5.0)
    """

    def __init__(
        self,
        tolerance: float = 0.1,
        max_buffer_size: int = 1000,
        time_offset: float = 0.0,
    ) -> None:
        """
        Initialize synchronizer.

        Args:
            tolerance: Time tolerance for matching (seconds)
            max_buffer_size: Maximum items to keep in buffer
            time_offset: Offset to apply to all timestamps
        """
        self._tolerance = tolerance
        self._max_buffer_size = max_buffer_size
        self._time_offset = time_offset

        # Data buffers (sorted by timestamp)
        self._pose_buffer: List[TimestampedData] = []
        self._action_buffer: List[TimestampedData] = []
        self._asr_buffer: List[TimestampedData] = []
        self._event_buffer: List[TimestampedData] = []

        # Timestamps for fast lookup
        self._pose_timestamps: List[float] = []
        self._action_timestamps: List[float] = []
        self._asr_timestamps: List[float] = []
        self._event_timestamps: List[float] = []

        # Frame counter
        self._frame_counter = 0

        # Callbacks for real-time processing
        self._callbacks: Dict[DataType, List[Callable]] = {
            DataType.POSE: [],
            DataType.ACTION: [],
            DataType.ASR: [],
            DataType.EVENT: [],
        }

    def add_pose(
        self,
        timestamp: float,
        pose_result: Any,
        source: str = "mediapipe",
        confidence: float = 1.0,
    ) -> None:
        """Add pose detection result."""
        self._add_data(
            self._pose_buffer,
            self._pose_timestamps,
            timestamp,
            pose_result,
            DataType.POSE,
            source,
            confidence,
        )
        self._notify_callbacks(DataType.POSE, pose_result)

    def add_action(
        self,
        timestamp: float,
        action_event: Any,
        source: str = "stgcn",
        confidence: float = 1.0,
    ) -> None:
        """Add action recognition event."""
        self._add_data(
            self._action_buffer,
            self._action_timestamps,
            timestamp,
            action_event,
            DataType.ACTION,
            source,
            confidence,
        )
        self._notify_callbacks(DataType.ACTION, action_event)

    def add_asr(
        self,
        timestamp: float,
        asr_result: Any,
        source: str = "hybrid",
        confidence: float = 1.0,
    ) -> None:
        """Add speech recognition result."""
        self._add_data(
            self._asr_buffer,
            self._asr_timestamps,
            timestamp,
            asr_result,
            DataType.ASR,
            source,
            confidence,
        )
        self._notify_callbacks(DataType.ASR, asr_result)

    def add_event(
        self,
        timestamp: float,
        event: Any,
        source: str = "system",
    ) -> None:
        """Add system event."""
        self._add_data(
            self._event_buffer,
            self._event_timestamps,
            timestamp,
            event,
            DataType.EVENT,
            source,
            1.0,
        )
        self._notify_callbacks(DataType.EVENT, event)

    def _add_data(
        self,
        buffer: List[TimestampedData],
        timestamps: List[float],
        timestamp: float,
        data: Any,
        data_type: DataType,
        source: str,
        confidence: float,
    ) -> None:
        """Add data to buffer in sorted order."""
        adjusted_ts = timestamp + self._time_offset

        item = TimestampedData(
            timestamp=adjusted_ts,
            data=data,
            data_type=data_type,
            source=source,
            confidence=confidence,
        )

        # Insert in sorted order
        idx = bisect.bisect_left(timestamps, adjusted_ts)
        timestamps.insert(idx, adjusted_ts)
        buffer.insert(idx, item)

        # Trim buffer if too large
        while len(buffer) > self._max_buffer_size:
            buffer.pop(0)
            timestamps.pop(0)

    def get_synced_frame(
        self,
        timestamp: float,
        tolerance: Optional[float] = None,
    ) -> SyncedFrame:
        """
        Get synchronized data at a specific timestamp.

        Args:
            timestamp: Target timestamp
            tolerance: Override default tolerance

        Returns:
            SyncedFrame with aligned data
        """
        tol = tolerance if tolerance is not None else self._tolerance
        adjusted_ts = timestamp + self._time_offset

        self._frame_counter += 1

        frame = SyncedFrame(
            timestamp=adjusted_ts,
            frame_number=self._frame_counter,
        )

        # Find nearest pose
        pose_data = self._find_nearest(
            self._pose_buffer, self._pose_timestamps, adjusted_ts, tol
        )
        if pose_data:
            frame.pose = pose_data.data
            frame.has_pose = True

        # Find nearest action
        action_data = self._find_nearest(
            self._action_buffer, self._action_timestamps, adjusted_ts, tol
        )
        if action_data:
            frame.action = action_data.data
            frame.has_action = True

        # Find nearest ASR
        asr_data = self._find_nearest(
            self._asr_buffer, self._asr_timestamps, adjusted_ts, tol
        )
        if asr_data:
            frame.has_asr = True
            # Extract text from ASR result
            if hasattr(asr_data.data, 'text'):
                frame.asr_text = asr_data.data.text
            elif isinstance(asr_data.data, str):
                frame.asr_text = asr_data.data
            elif isinstance(asr_data.data, dict):
                frame.asr_text = asr_data.data.get('text', '')

        # Find events in range
        events = self._find_in_range(
            self._event_buffer, self._event_timestamps,
            adjusted_ts - tol, adjusted_ts + tol
        )
        frame.events = [e.data for e in events]

        return frame

    def get_frames_in_range(
        self,
        start: float,
        end: float,
        step: float = 0.033,  # ~30fps
    ) -> List[SyncedFrame]:
        """
        Get synchronized frames for a time range.

        Args:
            start: Start timestamp
            end: End timestamp
            step: Time step between frames

        Returns:
            List of SyncedFrame objects
        """
        frames = []
        t = start

        while t <= end:
            frame = self.get_synced_frame(t)
            frames.append(frame)
            t += step

        return frames

    def _find_nearest(
        self,
        buffer: List[TimestampedData],
        timestamps: List[float],
        target: float,
        tolerance: float,
    ) -> Optional[TimestampedData]:
        """Find nearest data within tolerance."""
        if not timestamps:
            return None

        idx = bisect.bisect_left(timestamps, target)

        candidates = []

        # Check item at idx
        if idx < len(timestamps):
            diff = abs(timestamps[idx] - target)
            if diff <= tolerance:
                candidates.append((diff, buffer[idx]))

        # Check item before idx
        if idx > 0:
            diff = abs(timestamps[idx - 1] - target)
            if diff <= tolerance:
                candidates.append((diff, buffer[idx - 1]))

        if not candidates:
            return None

        # Return closest
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def _find_in_range(
        self,
        buffer: List[TimestampedData],
        timestamps: List[float],
        start: float,
        end: float,
    ) -> List[TimestampedData]:
        """Find all data within a time range."""
        if not timestamps:
            return []

        start_idx = bisect.bisect_left(timestamps, start)
        end_idx = bisect.bisect_right(timestamps, end)

        return buffer[start_idx:end_idx]

    def register_callback(
        self,
        data_type: DataType,
        callback: Callable[[Any], None],
    ) -> None:
        """Register a callback for real-time processing."""
        if data_type in self._callbacks:
            self._callbacks[data_type].append(callback)

    def unregister_callback(
        self,
        data_type: DataType,
        callback: Callable[[Any], None],
    ) -> None:
        """Unregister a callback."""
        if data_type in self._callbacks:
            try:
                self._callbacks[data_type].remove(callback)
            except ValueError:
                pass

    def _notify_callbacks(self, data_type: DataType, data: Any) -> None:
        """Notify registered callbacks."""
        for callback in self._callbacks.get(data_type, []):
            try:
                callback(data)
            except Exception:
                pass  # Don't let callback errors affect main flow

    def get_latest(
        self,
        data_type: DataType,
    ) -> Optional[TimestampedData]:
        """Get the latest data of a specific type."""
        buffer_map = {
            DataType.POSE: self._pose_buffer,
            DataType.ACTION: self._action_buffer,
            DataType.ASR: self._asr_buffer,
            DataType.EVENT: self._event_buffer,
        }

        buffer = buffer_map.get(data_type, [])
        return buffer[-1] if buffer else None

    def get_buffer_size(self, data_type: DataType) -> int:
        """Get current buffer size for a data type."""
        buffer_map = {
            DataType.POSE: self._pose_buffer,
            DataType.ACTION: self._action_buffer,
            DataType.ASR: self._asr_buffer,
            DataType.EVENT: self._event_buffer,
        }
        return len(buffer_map.get(data_type, []))

    def clear(self) -> None:
        """Clear all buffers."""
        self._pose_buffer.clear()
        self._action_buffer.clear()
        self._asr_buffer.clear()
        self._event_buffer.clear()
        self._pose_timestamps.clear()
        self._action_timestamps.clear()
        self._asr_timestamps.clear()
        self._event_timestamps.clear()
        self._frame_counter = 0

    def set_time_offset(self, offset: float) -> None:
        """Set time offset for synchronization."""
        self._time_offset = offset

    @property
    def tolerance(self) -> float:
        """Get current tolerance."""
        return self._tolerance

    @tolerance.setter
    def tolerance(self, value: float) -> None:
        """Set tolerance."""
        self._tolerance = value
