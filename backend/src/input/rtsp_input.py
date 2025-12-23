"""
RTSP Input - Network video stream reader implementation.

Reads video frames from RTSP/HTTP network streams.
"""

import queue
import threading
import time
from typing import Optional, Tuple

import cv2

from .video_source import VideoFrame, VideoSource, VideoSourceInfo, VideoSourceType


class RTSPInput(VideoSource):
    """
    RTSP/Network stream input source.

    Captures frames from network video streams (RTSP, HTTP, etc.).
    Uses a separate thread for reading to handle network latency
    and prevent frame dropping.

    Supported protocols:
        - RTSP: rtsp://host:port/path
        - HTTP: http://host:port/path
        - HTTPS: https://host:port/path

    Usage:
        with RTSPInput("rtsp://192.168.1.100:554/stream") as stream:
            for frame in stream:
                # Process frame.data
                pass

        # With reconnection:
        stream = RTSPInput(url, reconnect=True, reconnect_attempts=5)
    """

    def __init__(
        self,
        url: str,
        buffer_size: int = 2,
        timeout: float = 10.0,
        reconnect: bool = True,
        reconnect_attempts: int = 3,
        reconnect_delay: float = 2.0,
    ) -> None:
        """
        Initialize RTSP input.

        Args:
            url: RTSP/HTTP stream URL
            buffer_size: Frame buffer size (reduces latency)
            timeout: Connection timeout in seconds
            reconnect: Enable automatic reconnection on failure
            reconnect_attempts: Maximum reconnection attempts
            reconnect_delay: Delay between reconnection attempts
        """
        super().__init__()

        self._url = url
        self._buffer_size = buffer_size
        self._timeout = timeout
        self._reconnect = reconnect
        self._reconnect_attempts = reconnect_attempts
        self._reconnect_delay = reconnect_delay

        # Frame buffer for async reading
        self._frame_queue: queue.Queue[Optional[VideoFrame]] = queue.Queue(
            maxsize=buffer_size
        )

        # Threading control
        self._read_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()

        # Video properties (will be set after connection)
        self._width = 0
        self._height = 0
        self._fps = 30.0  # Default, may be updated

        self._cap: Optional[cv2.VideoCapture] = None
        self._connection_attempts = 0
        self._start_time = time.time()

        # Start connection
        if not self._connect():
            raise RuntimeError(f"Failed to connect to stream: {url}")

        # Start background reading thread
        self._start_reading_thread()

    def _connect(self) -> bool:
        """
        Establish connection to the stream.

        Returns:
            True if connection successful
        """
        # Set environment variable for faster RTSP connection
        # This is applied when OpenCV reads the stream
        self._cap = cv2.VideoCapture(self._url, cv2.CAP_FFMPEG)

        # Set buffer size to reduce latency
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, self._buffer_size)

        # Wait for connection with timeout
        start_time = time.time()
        while not self._cap.isOpened() and (time.time() - start_time) < self._timeout:
            time.sleep(0.1)

        if not self._cap.isOpened():
            return False

        # Get stream properties
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            self._fps = fps

        self._is_opened = True
        self._connected_event.set()
        return True

    def _reconnect_stream(self) -> bool:
        """
        Attempt to reconnect to the stream.

        Returns:
            True if reconnection successful
        """
        self._connected_event.clear()

        for attempt in range(self._reconnect_attempts):
            self._connection_attempts += 1

            if self._cap is not None:
                self._cap.release()

            time.sleep(self._reconnect_delay)

            if self._connect():
                return True

        return False

    def _start_reading_thread(self) -> None:
        """Start the background frame reading thread."""
        self._stop_event.clear()
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    def _read_loop(self) -> None:
        """Background thread loop for reading frames."""
        while not self._stop_event.is_set():
            if not self._connected_event.is_set():
                time.sleep(0.1)
                continue

            if self._cap is None or not self._cap.isOpened():
                if self._reconnect:
                    if not self._reconnect_stream():
                        break
                else:
                    break
                continue

            ret, frame_data = self._cap.read()

            if not ret:
                if self._reconnect:
                    if not self._reconnect_stream():
                        break
                    continue
                else:
                    break

            timestamp = time.time() - self._start_time if hasattr(self, '_start_time') else 0

            frame = VideoFrame(
                data=frame_data,
                timestamp=timestamp,
                frame_number=self._frame_count,
                width=self._width,
                height=self._height,
            )

            # Put frame in queue (drop oldest if full)
            try:
                self._frame_queue.put_nowait(frame)
            except queue.Full:
                try:
                    self._frame_queue.get_nowait()  # Remove oldest
                    self._frame_queue.put_nowait(frame)
                except queue.Empty:
                    pass

            self._frame_count += 1

        # Signal end of stream
        try:
            self._frame_queue.put_nowait(None)
        except queue.Full:
            pass

        self._is_opened = False

    def read_frame(self) -> Tuple[bool, Optional[VideoFrame]]:
        """
        Read a single frame from the stream buffer.

        Returns:
            Tuple of (success, VideoFrame or None)
        """
        if not self._is_opened:
            return False, None

        try:
            frame = self._frame_queue.get(timeout=self._timeout)
            if frame is None:
                self._is_opened = False
                return False, None
            return True, frame
        except queue.Empty:
            return False, None

    def get_fps(self) -> float:
        """Get stream frame rate."""
        return self._fps

    def get_frame_size(self) -> Tuple[int, int]:
        """Get frame dimensions (width, height)."""
        return self._width, self._height

    def release(self) -> None:
        """Release stream resources."""
        self._stop_event.set()
        self._is_opened = False

        if self._read_thread is not None and self._read_thread.is_alive():
            self._read_thread.join(timeout=2.0)

        if self._cap is not None:
            self._cap.release()

    def is_opened(self) -> bool:
        """Check if stream is open."""
        return self._is_opened

    def get_info(self) -> VideoSourceInfo:
        """Get stream source information."""
        return VideoSourceInfo(
            source_type=VideoSourceType.RTSP,
            width=self._width,
            height=self._height,
            fps=self._fps,
            total_frames=None,  # Live stream
            duration=None,  # Live stream
            source_path=self._url,
        )

    def get_buffer_size(self) -> int:
        """Get current buffer queue size."""
        return self._frame_queue.qsize()

    def get_connection_attempts(self) -> int:
        """Get total connection/reconnection attempts."""
        return self._connection_attempts

    @property
    def url(self) -> str:
        """Get stream URL."""
        return self._url

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to stream."""
        return self._connected_event.is_set()
