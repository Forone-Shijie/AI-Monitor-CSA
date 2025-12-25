"""
WebSocket Routes - Real-time monitoring via WebSocket.

Endpoints:
- WS /ws/live/{session_id} - Live monitoring data stream
- WS /ws/stream/{session_id} - Receive video frames from browser for processing
"""

import asyncio
import io
import json
import time
from typing import Any, Dict, List, Optional, Set

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from PIL import Image

from ..schemas import MonitoringFrame, PoseData, SessionStatus, WSMessage
from ..session_manager import session_manager
from ...perception.mediapipe_pose import MediaPipePose

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    WebSocket connection manager.

    Manages active WebSocket connections and broadcasts
    monitoring data to subscribed clients.
    """

    def __init__(self) -> None:
        """Initialize connection manager."""
        # session_id -> set of websockets
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
    ) -> bool:
        """
        Accept and register WebSocket connection.

        Args:
            websocket: WebSocket connection
            session_id: Session to subscribe to

        Returns:
            True if connected successfully
        """
        await websocket.accept()

        async with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = set()
            self._connections[session_id].add(websocket)

        return True

    async def disconnect(
        self,
        websocket: WebSocket,
        session_id: str,
    ) -> None:
        """Remove WebSocket connection."""
        async with self._lock:
            if session_id in self._connections:
                self._connections[session_id].discard(websocket)
                if not self._connections[session_id]:
                    del self._connections[session_id]

    async def broadcast(
        self,
        session_id: str,
        message: WSMessage,
    ) -> None:
        """Broadcast message to all connections for a session."""
        async with self._lock:
            connections = self._connections.get(session_id, set()).copy()

        if not connections:
            return

        # Convert to JSON
        data = message.model_dump()
        json_str = json.dumps(data, default=str)

        # Send to all connections
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(json_str)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self._connections.get(session_id, set()).discard(ws)

    async def send_personal(
        self,
        websocket: WebSocket,
        message: WSMessage,
    ) -> bool:
        """Send message to a specific connection."""
        try:
            data = message.model_dump()
            json_str = json.dumps(data, default=str)
            await websocket.send_text(json_str)
            return True
        except Exception:
            return False

    def get_connection_count(self, session_id: str) -> int:
        """Get number of connections for a session."""
        return len(self._connections.get(session_id, set()))

    @property
    def total_connections(self) -> int:
        """Get total number of connections."""
        return sum(len(conns) for conns in self._connections.values())


# Global connection manager
ws_manager = ConnectionManager()


@router.websocket("/ws/live/{session_id}")
async def websocket_live(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for live monitoring data.

    Streams real-time monitoring data for a session including:
    - Pose detection results
    - Action recognition events
    - ASR transcriptions
    - Brace position compliance

    Messages are sent as JSON with format:
    {
        "type": "frame" | "status" | "event" | "error",
        "data": {...},
        "timestamp": 1234567890.123
    }
    """
    # Check if session exists
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    # Accept connection
    await ws_manager.connect(websocket, session_id)

    # Send initial status
    await ws_manager.send_personal(
        websocket,
        WSMessage(
            type="connected",
            data={
                "session_id": session_id,
                "status": session.status.value,
                "message": "Connected to live stream",
            },
        ),
    )

    # Register frame callback
    async def on_frame(frame: MonitoringFrame):
        if frame.session_id == session_id:
            await ws_manager.broadcast(
                session_id,
                WSMessage(
                    type="frame",
                    data=frame.model_dump(),
                ),
            )

    # Note: In production, use proper async callback registration
    # For now, we'll use polling approach

    try:
        while True:
            try:
                # Wait for client messages
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0,
                )

                # Handle client commands
                try:
                    msg = json.loads(data)
                    cmd = msg.get("command")

                    if cmd == "ping":
                        await ws_manager.send_personal(
                            websocket,
                            WSMessage(type="pong", data={}),
                        )

                    elif cmd == "status":
                        status = session_manager.get_monitoring_status(session_id)
                        await ws_manager.send_personal(
                            websocket,
                            WSMessage(
                                type="status",
                                data=status.model_dump() if status else {},
                            ),
                        )

                except json.JSONDecodeError:
                    await ws_manager.send_personal(
                        websocket,
                        WSMessage(
                            type="error",
                            data={"message": "Invalid JSON"},
                        ),
                    )

            except asyncio.TimeoutError:
                # Send periodic status updates
                session = session_manager.get_session(session_id)
                if session:
                    if session.status == SessionStatus.COMPLETED:
                        await ws_manager.send_personal(
                            websocket,
                            WSMessage(
                                type="session_ended",
                                data={"session_id": session_id},
                            ),
                        )
                        break
                continue

    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket, session_id)


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """
    WebSocket endpoint for system monitoring.

    Provides system-wide monitoring data including:
    - Active sessions
    - Connection counts
    - System status
    """
    await websocket.accept()

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=5.0,
                )

                try:
                    msg = json.loads(data)
                    cmd = msg.get("command")

                    if cmd == "stats":
                        await websocket.send_json({
                            "type": "stats",
                            "data": {
                                "total_sessions": session_manager.session_count,
                                "active_session": session_manager.active_session_id,
                                "ws_connections": ws_manager.total_connections,
                            },
                            "timestamp": time.time(),
                        })

                    elif cmd == "sessions":
                        sessions = session_manager.list_sessions(limit=20)
                        await websocket.send_json({
                            "type": "sessions",
                            "data": [s.model_dump() for s in sessions],
                            "timestamp": time.time(),
                        })

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON"},
                        "timestamp": time.time(),
                    })

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": time.time(),
                })

    except WebSocketDisconnect:
        pass


# Helper function to broadcast frame from session manager
async def broadcast_frame(frame: MonitoringFrame) -> None:
    """Broadcast monitoring frame to WebSocket clients."""
    await ws_manager.broadcast(
        frame.session_id,
        WSMessage(
            type="frame",
            data=frame.model_dump(),
        ),
    )


async def broadcast_event(
    session_id: str,
    event_type: str,
    data: dict,
) -> None:
    """Broadcast event to WebSocket clients."""
    await ws_manager.broadcast(
        session_id,
        WSMessage(
            type="event",
            data={
                "event_type": event_type,
                **data,
            },
        ),
    )


class FrameProcessor:
    """
    Process video frames from browser using MediaPipe pose detection.

    Maintains a pose detector instance per session for efficient processing.
    """

    def __init__(self) -> None:
        """Initialize frame processor."""
        self._detectors: Dict[str, MediaPipePose] = {}
        self._frame_counts: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def get_detector(self, session_id: str) -> MediaPipePose:
        """Get or create pose detector for session."""
        async with self._lock:
            if session_id not in self._detectors:
                self._detectors[session_id] = MediaPipePose(
                    model_complexity=1,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                    static_image_mode=True,  # Process each frame independently
                )
                self._frame_counts[session_id] = 0
            return self._detectors[session_id]

    async def process_frame(
        self,
        session_id: str,
        frame_data: bytes,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a video frame and return pose detection results.

        Args:
            session_id: Session identifier
            frame_data: JPEG image bytes from browser

        Returns:
            Detection results as dict, or None if processing failed
        """
        try:
            # Decode JPEG to numpy array
            image = Image.open(io.BytesIO(frame_data))
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            print(f"[Frame] Session {session_id}: received {len(frame_data)} bytes, decoded to {frame.shape}")

            # Get detector for this session
            detector = await self.get_detector(session_id)
            print(f"[MediaPipe] Detector initialized: {detector.is_initialized}")

            # Increment frame count
            async with self._lock:
                self._frame_counts[session_id] += 1
                frame_number = self._frame_counts[session_id]

            # Detect pose
            result = detector.detect(frame)
            print(f"[Pose] Frame #{frame_number}: detected={result.detected}, confidence={result.confidence:.3f}")

            # Convert result to API format
            pose_data: Optional[Dict[str, Any]] = None
            if result.detected:
                # Convert landmarks to list format
                keypoints = [
                    [lm.x, lm.y, lm.z, lm.visibility]
                    for lm in result.landmarks
                ] if result.landmarks else None
                print(f"[Pose] Landmarks: {len(result.landmarks) if result.landmarks else 0}, pose_type={result.pose_type.value}")

                # Convert angles to dict
                angles = result.angles.to_dict() if result.angles else None

                pose_data = {
                    "timestamp": result.timestamp,
                    "detected": True,
                    "keypoints": keypoints,
                    "angles": angles,
                    "pose_type": result.pose_type.value,
                    "confidence": result.confidence,
                }
            else:
                pose_data = {
                    "timestamp": time.time(),
                    "detected": False,
                    "confidence": 0.0,
                }

            return {
                "session_id": session_id,
                "frame_number": frame_number,
                "timestamp": time.time(),
                "pose": pose_data,
            }

        except Exception as e:
            print(f"Frame processing error: {e}")
            return None

    async def cleanup_session(self, session_id: str) -> None:
        """Release resources for a session."""
        async with self._lock:
            if session_id in self._detectors:
                self._detectors[session_id].release()
                del self._detectors[session_id]
            if session_id in self._frame_counts:
                del self._frame_counts[session_id]

    async def cleanup_all(self) -> None:
        """Release all detector resources."""
        async with self._lock:
            for detector in self._detectors.values():
                detector.release()
            self._detectors.clear()
            self._frame_counts.clear()


# Global frame processor
frame_processor = FrameProcessor()


@router.websocket("/ws/stream/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for receiving video frames from browser.

    Accepts binary WebSocket messages containing JPEG frame data,
    processes them through MediaPipe pose detection, and returns
    detection results as JSON.

    Protocol:
    - Client sends: Binary (JPEG image bytes)
    - Server responds: JSON with pose detection results

    Response format:
    {
        "type": "frame_result",
        "data": {
            "session_id": "...",
            "frame_number": 123,
            "timestamp": 1234567890.123,
            "pose": {
                "detected": true,
                "keypoints": [[x, y, z, visibility], ...],
                "angles": {...},
                "pose_type": "brace_position",
                "confidence": 0.95
            }
        }
    }
    """
    # Check if session exists
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    # Accept connection
    await websocket.accept()

    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "data": {
            "session_id": session_id,
            "message": "Ready to receive video frames",
        },
        "timestamp": time.time(),
    })

    try:
        while True:
            # Receive frame data (binary)
            data = await websocket.receive()

            # Check for disconnect
            if data.get("type") == "websocket.disconnect":
                break

            if "bytes" in data:
                # Process binary frame
                frame_data = data["bytes"]
                result = await frame_processor.process_frame(session_id, frame_data)

                if result:
                    # Send detection result
                    await websocket.send_json({
                        "type": "frame_result",
                        "data": result,
                        "timestamp": time.time(),
                    })

                    # Also broadcast to live subscribers
                    await ws_manager.broadcast(
                        session_id,
                        WSMessage(
                            type="frame",
                            data=result,
                        ),
                    )
                else:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Frame processing failed"},
                        "timestamp": time.time(),
                    })

            elif "text" in data:
                # Handle JSON commands
                try:
                    msg = json.loads(data["text"])
                    cmd = msg.get("command")

                    if cmd == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": time.time(),
                        })
                    elif cmd == "stop":
                        break

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON"},
                        "timestamp": time.time(),
                    })

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup detector for this session
        await frame_processor.cleanup_session(session_id)


# =============================================================================
# Audio Processing for ASR
# =============================================================================


class AudioProcessor:
    """
    Process audio data from browser using local ASR.

    NOTE: ASR engine implementation pending.
    FunASR Paraformer will be integrated for streaming recognition.
    Maintains an ASR engine instance per session.
    """

    def __init__(self) -> None:
        """Initialize audio processor."""
        self._asr_engines: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get_asr_engine(self, session_id: str) -> Any:
        """Get or create ASR engine for session."""
        async with self._lock:
            if session_id not in self._asr_engines:
                # TODO: Implement FunASR Paraformer integration
                print(f"[ASR] ASR engine not implemented yet for session {session_id}")
                return None
            return self._asr_engines[session_id]

    async def process_audio(
        self,
        session_id: str,
        audio_data: bytes,
        sample_rate: int = 16000,
    ) -> Optional[Dict[str, Any]]:
        """
        Process audio data and return ASR results.

        Args:
            session_id: Session identifier
            audio_data: PCM audio bytes (16-bit, mono)
            sample_rate: Audio sample rate

        Returns:
            ASR result as dict, or None if processing failed
        """
        # TODO: Implement FunASR Paraformer integration
        print(f"[ASR] Audio processing not implemented yet")
        return None

    async def cleanup_session(self, session_id: str) -> None:
        """Release resources for a session."""
        async with self._lock:
            if session_id in self._asr_engines:
                engine = self._asr_engines[session_id]
                if hasattr(engine, 'release'):
                    engine.release()
                del self._asr_engines[session_id]
            print(f"[ASR] Cleaned up session {session_id}")

    async def cleanup_all(self) -> None:
        """Release all ASR resources."""
        async with self._lock:
            for engine in self._asr_engines.values():
                if hasattr(engine, 'release'):
                    engine.release()
            self._asr_engines.clear()


# Global audio processor
audio_processor = AudioProcessor()


@router.websocket("/ws/audio/{session_id}")
async def websocket_audio(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for receiving audio data from browser.

    Accepts binary WebSocket messages containing PCM audio data,
    processes them through ASR, and returns transcription results.

    Protocol:
    - Client sends: Binary (PCM 16-bit audio bytes)
    - Server responds: JSON with ASR results

    Response format:
    {
        "type": "asr_result",
        "data": {
            "session_id": "...",
            "timestamp": 1234567890.123,
            "text": "识别的文字",
            "confidence": 0.95,
            "segments": [...]
        }
    }
    """
    # Check if session exists
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    # Accept connection
    await websocket.accept()

    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "data": {
            "session_id": session_id,
            "message": "Ready to receive audio data",
        },
        "timestamp": time.time(),
    })

    try:
        while True:
            # Receive audio data (binary)
            data = await websocket.receive()

            # Check for disconnect
            if data.get("type") == "websocket.disconnect":
                break

            if "bytes" in data:
                # Process binary audio
                audio_data = data["bytes"]
                result = await audio_processor.process_audio(session_id, audio_data)

                if result:
                    # Send ASR result
                    await websocket.send_json({
                        "type": "asr_result",
                        "data": result,
                        "timestamp": time.time(),
                    })

                    # Also broadcast to live subscribers
                    await ws_manager.broadcast(
                        session_id,
                        WSMessage(
                            type="asr",
                            data=result,
                        ),
                    )

            elif "text" in data:
                # Handle JSON commands
                try:
                    msg = json.loads(data["text"])
                    cmd = msg.get("command")

                    if cmd == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": time.time(),
                        })
                    elif cmd == "stop":
                        break

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON"},
                        "timestamp": time.time(),
                    })

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup ASR for this session
        await audio_processor.cleanup_session(session_id)
