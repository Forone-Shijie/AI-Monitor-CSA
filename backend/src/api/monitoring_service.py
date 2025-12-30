"""
Monitoring Service - Manages real-time monitoring pipeline.

Handles:
- Camera/video input
- Pose detection
- ASR processing
- Frame data broadcasting
"""

import asyncio
import math
import random
import threading
import time
from typing import Callable, Dict, Optional

import numpy as np

from .schemas import VideoSourceType
from .session_manager import session_manager

# Lazy imports for video/perception modules (may not be available in all environments)
CameraInput = None
FileInput = None
RTMPoseDetector = None


def _load_video_modules():
    """Lazy load video modules."""
    global CameraInput, FileInput
    if CameraInput is None:
        try:
            from src.input.camera_input import CameraInput as _CameraInput
            from src.input.file_input import FileInput as _FileInput
            CameraInput = _CameraInput
            FileInput = _FileInput
        except ImportError:
            pass


def _load_perception_modules():
    """Lazy load perception modules (RTMPose for GPU-accelerated pose detection)."""
    global RTMPoseDetector
    if RTMPoseDetector is None:
        try:
            from src.perception.rtmpose_detector import RTMPoseDetector as _RTMPoseDetector
            RTMPoseDetector = _RTMPoseDetector
        except ImportError:
            pass


class MonitoringService:
    """
    Real-time monitoring service.

    Manages the monitoring pipeline including video capture,
    pose detection, and data broadcasting.

    Usage:
        service = MonitoringService()

        # Start monitoring for a session
        await service.start(session_id)

        # Stop monitoring
        await service.stop(session_id)
    """

    def __init__(self) -> None:
        """Initialize monitoring service."""
        self._active_monitors: Dict[str, "MonitoringTask"] = {}
        self._lock = threading.Lock()

    async def start(
        self,
        session_id: str,
        video_source: VideoSourceType = VideoSourceType.CAMERA,
        video_path: Optional[str] = None,
        camera_id: int = 0,
        require_camera: bool = False,
    ) -> bool:
        """
        Start monitoring for a session.

        Args:
            session_id: Session to monitor
            video_source: Video source type
            video_path: Path for file input
            camera_id: Camera ID for camera input
            require_camera: If True, raise error when camera unavailable

        Returns:
            True if started successfully

        Raises:
            RuntimeError: If require_camera is True and camera is unavailable
        """
        with self._lock:
            if session_id in self._active_monitors:
                return False

            # Determine if we need simulation mode
            simulation_mode = False
            if video_source == VideoSourceType.CAMERA:
                # Check if camera is available
                if not self._is_camera_available(camera_id):
                    if require_camera:
                        raise RuntimeError(f"摄像头 {camera_id} 不可用，请检查设备连接或选择其他设备")
                    print(f"[MonitoringService] Camera {camera_id} not available, using simulation mode")
                    simulation_mode = True

            try:
                task = MonitoringTask(
                    session_id=session_id,
                    video_source=video_source,
                    video_path=video_path,
                    camera_id=camera_id,
                    simulation_mode=simulation_mode,
                )
                self._active_monitors[session_id] = task
                task.start()
                return True
            except Exception as e:
                print(f"Failed to start monitoring: {e}")
                return False

    def _is_camera_available(self, camera_id: int) -> bool:
        """Check if a camera is available."""
        try:
            import cv2
            cap = cv2.VideoCapture(camera_id)
            available = cap.isOpened()
            cap.release()
            return available
        except Exception:
            return False

    async def stop(self, session_id: str) -> bool:
        """
        Stop monitoring for a session.

        Args:
            session_id: Session to stop

        Returns:
            True if stopped successfully
        """
        with self._lock:
            task = self._active_monitors.pop(session_id, None)
            if task:
                task.stop()
                return True
            return False

    def is_running(self, session_id: str) -> bool:
        """Check if monitoring is running for a session."""
        with self._lock:
            task = self._active_monitors.get(session_id)
            return task is not None and task.is_running

    def get_status(self, session_id: str) -> Optional[Dict]:
        """Get monitoring status for a session."""
        with self._lock:
            task = self._active_monitors.get(session_id)
            if task:
                return {
                    "is_running": task.is_running,
                    "frame_count": task.frame_count,
                    "fps": task.current_fps,
                    "video_source": task.video_source_type,
                }
            return None


class MonitoringTask:
    """
    Individual monitoring task for a session.

    Runs in a background thread to capture and process frames.
    Supports simulation mode when camera is not available.
    """

    def __init__(
        self,
        session_id: str,
        video_source: VideoSourceType = VideoSourceType.CAMERA,
        video_path: Optional[str] = None,
        camera_id: int = 0,
        target_fps: float = 30.0,
        simulation_mode: bool = False,
    ) -> None:
        """Initialize monitoring task."""
        self.session_id = session_id
        self.video_source_type = video_source
        self.video_path = video_path
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.simulation_mode = simulation_mode

        self._video_source = None
        self._pose_detector = None

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False

        self.frame_count = 0
        self.current_fps = 0.0
        self._last_fps_time = 0.0
        self._fps_frame_count = 0

    def start(self) -> None:
        """Start the monitoring task."""
        if self._is_running:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._is_running = True

    def stop(self) -> None:
        """Stop the monitoring task."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self._is_running = False
        self._cleanup()

    def _run(self) -> None:
        """Main monitoring loop."""
        try:
            self._initialize()
            frame_interval = 1.0 / self.target_fps
            last_frame_time = time.time()

            while not self._stop_event.is_set():
                # Check if session is still running
                session = session_manager.get_session(self.session_id)
                if not session or session.status.value != "running":
                    break

                if self.simulation_mode:
                    # Generate simulated pose data
                    pose_data = self._generate_simulated_pose()
                else:
                    # Read frame from video source
                    if self._video_source is None:
                        break

                    success, frame = self._video_source.read_frame()
                    if not success or frame is None:
                        if self.video_source_type == VideoSourceType.FILE:
                            # End of file
                            break
                        continue

                    # Process frame
                    pose_data = self._process_pose(frame.data)

                # Send to session manager
                session_manager.add_frame_data(
                    self.session_id,
                    pose=pose_data,
                )

                self.frame_count += 1
                self._update_fps()

                # Frame rate control
                elapsed = time.time() - last_frame_time
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                last_frame_time = time.time()

        except Exception as e:
            print(f"Monitoring error for session {self.session_id}: {e}")
        finally:
            self._cleanup()
            self._is_running = False

    def _initialize(self) -> None:
        """Initialize video source and detectors."""
        if self.simulation_mode:
            # Simulation mode - no real hardware needed
            print(f"[MonitoringTask] Running in simulation mode for session {self.session_id}")
            return

        # Load modules
        _load_video_modules()
        _load_perception_modules()

        # Initialize video source
        if self.video_source_type == VideoSourceType.CAMERA:
            if CameraInput is None:
                raise RuntimeError("Camera input module not available")
            self._video_source = CameraInput(camera_id=self.camera_id)
        elif self.video_source_type == VideoSourceType.FILE and self.video_path:
            if FileInput is None:
                raise RuntimeError("File input module not available")
            self._video_source = FileInput(self.video_path)
        else:
            raise ValueError(f"Unsupported video source: {self.video_source_type}")

        # Initialize pose detector (RTMPose with GPU acceleration)
        if RTMPoseDetector is not None:
            self._pose_detector = RTMPoseDetector(
                device="cuda:0",
                det_score_thr=0.3,
                pose_score_thr=0.3,
                max_persons=5,
            )

    def _process_pose(self, frame: np.ndarray) -> Optional[Dict]:
        """Process frame for pose detection."""
        if self._pose_detector is None:
            return None

        result: PoseResult = self._pose_detector.detect(frame)

        if not result.detected:
            return {
                "timestamp": time.time(),
                "detected": False,
                "confidence": 0.0,
            }

        # Convert landmarks to serializable format
        keypoints = []
        if result.landmarks:
            for lm in result.landmarks:
                keypoints.append([lm.x, lm.y, lm.z, lm.visibility])

        # Convert angles to dict
        angles = {}
        if result.angles:
            angles = {
                "left_elbow": result.angles.left_elbow,
                "right_elbow": result.angles.right_elbow,
                "left_shoulder": result.angles.left_shoulder,
                "right_shoulder": result.angles.right_shoulder,
                "left_knee": result.angles.left_knee,
                "right_knee": result.angles.right_knee,
                "left_hip": result.angles.left_hip,
                "right_hip": result.angles.right_hip,
                "torso": result.angles.torso,
                "neck": result.angles.neck,
            }

        return {
            "timestamp": result.timestamp or time.time(),
            "detected": True,
            "keypoints": keypoints,
            "angles": angles,
            "pose_type": result.pose_type.value if result.pose_type else "unknown",
            "confidence": result.confidence,
        }

    def _generate_simulated_pose(self) -> Dict:
        """Generate simulated pose data for testing."""
        t = time.time()

        # Generate 33 keypoints (MediaPipe format) with slight animation
        keypoints = []
        base_positions = [
            # Face landmarks (0-10)
            (0.5, 0.15), (0.48, 0.12), (0.47, 0.12), (0.46, 0.13),
            (0.52, 0.12), (0.53, 0.12), (0.54, 0.13), (0.45, 0.14),
            (0.55, 0.14), (0.47, 0.17), (0.53, 0.17),
            # Body landmarks (11-32)
            (0.4, 0.25), (0.6, 0.25),   # shoulders
            (0.35, 0.4), (0.65, 0.4),   # elbows
            (0.3, 0.55), (0.7, 0.55),   # wrists
            (0.32, 0.58), (0.68, 0.58), # pinky
            (0.28, 0.58), (0.72, 0.58), # index
            (0.3, 0.56), (0.7, 0.56),   # thumb
            (0.42, 0.55), (0.58, 0.55), # hips
            (0.42, 0.75), (0.58, 0.75), # knees
            (0.42, 0.95), (0.58, 0.95), # ankles
            (0.4, 0.98), (0.6, 0.98),   # heels
            (0.38, 0.98), (0.62, 0.98), # foot index
        ]

        # Add slight movement animation
        phase = t * 0.5
        for i, (bx, by) in enumerate(base_positions):
            # Add subtle breathing/swaying motion
            dx = math.sin(phase + i * 0.1) * 0.01
            dy = math.cos(phase * 0.7 + i * 0.1) * 0.005
            x = bx + dx
            y = by + dy
            z = random.uniform(-0.1, 0.1)
            visibility = random.uniform(0.85, 0.99)
            keypoints.append([x, y, z, visibility])

        # Simulate different pose types based on time
        pose_cycle = int(t / 10) % 4
        pose_types = ["standing", "brace_position", "sitting", "bending"]
        pose_type = pose_types[pose_cycle]

        # Calculate simulated angles
        angles = {
            "left_elbow": 160 + math.sin(phase) * 10,
            "right_elbow": 160 + math.cos(phase) * 10,
            "left_shoulder": 30 + math.sin(phase * 0.5) * 5,
            "right_shoulder": 30 + math.cos(phase * 0.5) * 5,
            "left_knee": 170 + math.sin(phase * 0.3) * 5,
            "right_knee": 170 + math.cos(phase * 0.3) * 5,
            "left_hip": 175 + math.sin(phase * 0.2) * 3,
            "right_hip": 175 + math.cos(phase * 0.2) * 3,
            "torso": 5 + math.sin(phase * 0.1) * 2,
            "neck": 10 + math.cos(phase * 0.1) * 2,
        }

        return {
            "timestamp": t,
            "detected": True,
            "keypoints": keypoints,
            "angles": angles,
            "pose_type": pose_type,
            "confidence": random.uniform(0.88, 0.98),
        }

    def _update_fps(self) -> None:
        """Update FPS calculation."""
        current_time = time.time()
        self._fps_frame_count += 1

        if current_time - self._last_fps_time >= 1.0:
            self.current_fps = self._fps_frame_count / (current_time - self._last_fps_time)
            self._fps_frame_count = 0
            self._last_fps_time = current_time

    def _cleanup(self) -> None:
        """Cleanup resources."""
        if self._video_source:
            self._video_source.release()
            self._video_source = None

        if self._pose_detector:
            self._pose_detector.release()
            self._pose_detector = None

    @property
    def is_running(self) -> bool:
        """Check if task is running."""
        return self._is_running


# Global monitoring service instance
monitoring_service = MonitoringService()
