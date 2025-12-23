"""
Session Manager - Manages training sessions lifecycle.

Handles:
- Session creation and storage
- Session state management
- Monitoring coordination
- Data collection
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .schemas import (
    MonitoringFrame,
    MonitoringStatus,
    SessionInfo,
    SessionStatus,
    VideoSourceType,
)


@dataclass
class SessionData:
    """Internal session data storage."""

    session_id: str
    trainee_id: str
    trainee_name: str
    scenario_id: str
    scenario_name: str
    status: SessionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # Video source config
    video_source: VideoSourceType = VideoSourceType.CAMERA
    video_path: Optional[str] = None
    camera_id: int = 0

    # Monitoring data
    frame_count: int = 0
    last_frame_time: float = 0.0
    fps: float = 0.0

    # Collected data
    pose_history: List[Dict] = field(default_factory=list)
    action_history: List[Dict] = field(default_factory=list)
    asr_history: List[Dict] = field(default_factory=list)
    brace_history: List[Dict] = field(default_factory=list)
    events: List[Dict] = field(default_factory=list)

    # Results
    evaluation_result: Optional[Dict] = None
    report: Optional[Dict] = None

    def to_info(self) -> SessionInfo:
        """Convert to SessionInfo."""
        duration = 0.0
        if self.started_at:
            end = self.ended_at or datetime.now()
            duration = (end - self.started_at).total_seconds()

        return SessionInfo(
            session_id=self.session_id,
            trainee_id=self.trainee_id,
            trainee_name=self.trainee_name,
            scenario_id=self.scenario_id,
            scenario_name=self.scenario_name,
            status=self.status,
            created_at=self.created_at,
            started_at=self.started_at,
            ended_at=self.ended_at,
            duration_seconds=duration,
        )


class SessionManager:
    """
    Manages training session lifecycle.

    Handles session creation, state transitions, and data collection
    for training monitoring.

    Usage:
        manager = SessionManager()

        # Create session
        session = manager.create_session(
            trainee_id="T001",
            trainee_name="张三",
            scenario_id="brace_position",
        )

        # Start monitoring
        manager.start_session(session.session_id)

        # Add frame data
        manager.add_frame_data(session.session_id, frame_data)

        # Stop and get results
        manager.stop_session(session.session_id)
    """

    # Scenario name mapping
    SCENARIO_NAMES = {
        "brace_position": "防冲击姿势",
        "fire_emergency": "火警处置",
        "evacuation": "紧急撤离",
        "medical_emergency": "医疗紧急",
    }

    def __init__(self) -> None:
        """Initialize session manager."""
        self._sessions: Dict[str, SessionData] = {}
        self._active_session_id: Optional[str] = None
        self._frame_callbacks: List[Callable] = []
        self._status_callbacks: List[Callable] = []

    def create_session(
        self,
        trainee_id: str,
        trainee_name: str,
        scenario_id: str = "brace_position",
        video_source: VideoSourceType = VideoSourceType.CAMERA,
        video_path: Optional[str] = None,
        camera_id: int = 0,
    ) -> SessionInfo:
        """
        Create a new training session.

        Args:
            trainee_id: Trainee identifier
            trainee_name: Trainee name
            scenario_id: Scenario to monitor
            video_source: Video source type
            video_path: Video file path or RTSP URL
            camera_id: Camera device ID

        Returns:
            SessionInfo with new session data
        """
        session_id = self._generate_session_id()
        scenario_name = self.SCENARIO_NAMES.get(scenario_id, scenario_id)

        session = SessionData(
            session_id=session_id,
            trainee_id=trainee_id,
            trainee_name=trainee_name,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            status=SessionStatus.CREATED,
            created_at=datetime.now(),
            video_source=video_source,
            video_path=video_path,
            camera_id=camera_id,
        )

        self._sessions[session_id] = session
        return session.to_info()

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session by ID."""
        session = self._sessions.get(session_id)
        return session.to_info() if session else None

    def get_session_data(self, session_id: str) -> Optional[SessionData]:
        """Get raw session data."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
        trainee_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[SessionInfo]:
        """
        List sessions with optional filtering.

        Args:
            status: Filter by status
            trainee_id: Filter by trainee
            limit: Maximum results

        Returns:
            List of SessionInfo
        """
        sessions = list(self._sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]

        if trainee_id:
            sessions = [s for s in sessions if s.trainee_id == trainee_id]

        # Sort by created_at descending
        sessions.sort(key=lambda x: x.created_at, reverse=True)

        return [s.to_info() for s in sessions[:limit]]

    def start_session(
        self,
        session_id: str,
        trigger_type: str = "manual",
    ) -> bool:
        """
        Start monitoring for a session.

        Args:
            session_id: Session to start
            trigger_type: How monitoring was triggered

        Returns:
            True if started successfully
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session.status not in [SessionStatus.CREATED, SessionStatus.PAUSED]:
            return False

        session.status = SessionStatus.RUNNING
        session.started_at = session.started_at or datetime.now()
        session.last_frame_time = time.time()

        self._active_session_id = session_id

        # Add trigger event
        session.events.append({
            "type": "session_start",
            "trigger_type": trigger_type,
            "timestamp": time.time(),
        })

        self._notify_status_change(session_id)
        return True

    def pause_session(self, session_id: str) -> bool:
        """Pause monitoring for a session."""
        session = self._sessions.get(session_id)
        if not session or session.status != SessionStatus.RUNNING:
            return False

        session.status = SessionStatus.PAUSED
        session.events.append({
            "type": "session_pause",
            "timestamp": time.time(),
        })

        if self._active_session_id == session_id:
            self._active_session_id = None

        self._notify_status_change(session_id)
        return True

    def stop_session(
        self,
        session_id: str,
        generate_report: bool = True,
    ) -> bool:
        """
        Stop monitoring and complete session.

        Args:
            session_id: Session to stop
            generate_report: Whether to generate report

        Returns:
            True if stopped successfully
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session.status not in [SessionStatus.RUNNING, SessionStatus.PAUSED]:
            return False

        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now()

        session.events.append({
            "type": "session_stop",
            "timestamp": time.time(),
            "frame_count": session.frame_count,
        })

        if self._active_session_id == session_id:
            self._active_session_id = None

        self._notify_status_change(session_id)
        return True

    def cancel_session(self, session_id: str) -> bool:
        """Cancel a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = SessionStatus.CANCELLED
        session.ended_at = datetime.now()

        if self._active_session_id == session_id:
            self._active_session_id = None

        self._notify_status_change(session_id)
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id not in self._sessions:
            return False

        if self._active_session_id == session_id:
            self._active_session_id = None

        del self._sessions[session_id]
        return True

    def update_session(
        self,
        session_id: str,
        trainee_id: Optional[str] = None,
        trainee_name: Optional[str] = None,
        scenario_id: Optional[str] = None,
        camera_id: Optional[int] = None,
        audio_device_id: Optional[int] = None,
    ) -> Optional[SessionInfo]:
        """
        Update session parameters.

        Only allowed when session is not running.

        Args:
            session_id: Session to update
            trainee_id: New trainee identifier
            trainee_name: New trainee name
            scenario_id: New scenario ID
            camera_id: New camera device ID
            audio_device_id: New audio device ID (stored but not used yet)

        Returns:
            Updated SessionInfo, or None if update failed
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Only allow updates when not running
        if session.status == SessionStatus.RUNNING:
            return None

        # Update fields if provided
        if trainee_id is not None:
            session.trainee_id = trainee_id

        if trainee_name is not None:
            session.trainee_name = trainee_name

        if scenario_id is not None:
            session.scenario_id = scenario_id
            session.scenario_name = self.SCENARIO_NAMES.get(scenario_id, scenario_id)

        if camera_id is not None:
            session.camera_id = camera_id

        # Note: audio_device_id is accepted but SessionData doesn't have this field yet
        # This is fine for now - we can add it later when audio is implemented

        return session.to_info()

    def add_frame_data(
        self,
        session_id: str,
        pose: Optional[Dict] = None,
        action: Optional[Dict] = None,
        asr: Optional[Dict] = None,
        brace: Optional[Dict] = None,
    ) -> Optional[MonitoringFrame]:
        """
        Add monitoring data for a frame.

        Args:
            session_id: Session ID
            pose: Pose detection data
            action: Action recognition data
            asr: ASR data
            brace: Brace position data

        Returns:
            MonitoringFrame if added
        """
        session = self._sessions.get(session_id)
        if not session or session.status != SessionStatus.RUNNING:
            return None

        current_time = time.time()
        session.frame_count += 1

        # Calculate FPS
        if session.last_frame_time > 0:
            elapsed = current_time - session.last_frame_time
            if elapsed > 0:
                session.fps = 1.0 / elapsed
        session.last_frame_time = current_time

        # Store data
        if pose:
            pose["frame_number"] = session.frame_count
            session.pose_history.append(pose)

        if action:
            action["frame_number"] = session.frame_count
            session.action_history.append(action)

        if asr:
            asr["frame_number"] = session.frame_count
            session.asr_history.append(asr)

        if brace:
            brace["frame_number"] = session.frame_count
            session.brace_history.append(brace)

        # Create frame
        frame = MonitoringFrame(
            session_id=session_id,
            frame_number=session.frame_count,
            timestamp=current_time,
            pose=pose,
            action=action,
            asr=asr,
            brace=brace,
        )

        # Notify callbacks
        self._notify_frame(frame)

        return frame

    def add_event(
        self,
        session_id: str,
        event_type: str,
        data: Optional[Dict] = None,
    ) -> bool:
        """Add an event to the session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.events.append({
            "type": event_type,
            "timestamp": time.time(),
            "data": data or {},
        })
        return True

    def get_monitoring_status(self, session_id: str) -> Optional[MonitoringStatus]:
        """Get current monitoring status."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        elapsed = 0.0
        if session.started_at:
            end = session.ended_at or datetime.now()
            elapsed = (end - session.started_at).total_seconds()

        return MonitoringStatus(
            session_id=session_id,
            is_running=session.status == SessionStatus.RUNNING,
            frame_count=session.frame_count,
            elapsed_seconds=elapsed,
            fps=session.fps,
            last_update=datetime.fromtimestamp(session.last_frame_time)
            if session.last_frame_time > 0
            else None,
        )

    def set_evaluation_result(
        self,
        session_id: str,
        result: Dict,
    ) -> bool:
        """Set evaluation result for session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.evaluation_result = result
        return True

    def set_report(
        self,
        session_id: str,
        report: Dict,
    ) -> bool:
        """Set report for session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.report = report
        return True

    def register_frame_callback(
        self,
        callback: Callable[[MonitoringFrame], None],
    ) -> None:
        """Register callback for new frames."""
        self._frame_callbacks.append(callback)

    def unregister_frame_callback(
        self,
        callback: Callable[[MonitoringFrame], None],
    ) -> None:
        """Unregister frame callback."""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)

    def register_status_callback(
        self,
        callback: Callable[[str, SessionStatus], None],
    ) -> None:
        """Register callback for status changes."""
        self._status_callbacks.append(callback)

    def _notify_frame(self, frame: MonitoringFrame) -> None:
        """Notify frame callbacks."""
        for callback in self._frame_callbacks:
            try:
                callback(frame)
            except Exception:
                pass

    def _notify_status_change(self, session_id: str) -> None:
        """Notify status callbacks."""
        session = self._sessions.get(session_id)
        if not session:
            return

        for callback in self._status_callbacks:
            try:
                callback(session_id, session.status)
            except Exception:
                pass

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique = uuid.uuid4().hex[:8]
        return f"sess_{timestamp}_{unique}"

    @property
    def active_session_id(self) -> Optional[str]:
        """Get currently active session ID."""
        return self._active_session_id

    @property
    def session_count(self) -> int:
        """Get total session count."""
        return len(self._sessions)

    def clear_all(self) -> None:
        """Clear all sessions."""
        self._sessions.clear()
        self._active_session_id = None


# Global session manager instance
session_manager = SessionManager()
