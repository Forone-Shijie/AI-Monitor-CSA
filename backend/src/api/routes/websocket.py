"""
WebSocket Routes - Real-time monitoring via WebSocket.

Endpoints:
- WS /ws/live/{session_id} - Live monitoring data stream
- WS /ws/stream/{session_id} - Receive video frames from browser for processing
"""

import asyncio
import io
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from PIL import Image

from ..schemas import MonitoringFrame, PoseData, SessionStatus, WSMessage
from ..session_manager import session_manager
from ...perception.rtmpose_detector import RTMPoseDetector

# 配置日志
logger = logging.getLogger(__name__)

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
    Process video frames from browser using RTMPose (GPU-accelerated).

    Maintains a pose detector instance per session for efficient processing.
    Uses COCO 17-point keypoint format.
    """

    def __init__(self) -> None:
        """Initialize frame processor."""
        self._detectors: Dict[str, RTMPoseDetector] = {}
        self._frame_counts: Dict[str, int] = {}
        self._lock = asyncio.Lock()
        # ThreadPoolExecutor for async inference (avoid blocking event loop)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rtmpose")

    async def get_detector(self, session_id: str) -> RTMPoseDetector:
        """Get or create pose detector for session."""
        async with self._lock:
            if session_id not in self._detectors:
                self._detectors[session_id] = RTMPoseDetector(
                    device="cuda:0",
                    det_score_thr=0.3,
                    pose_score_thr=0.3,
                    max_persons=5,
                )
                self._frame_counts[session_id] = 0
            return self._detectors[session_id]

    async def process_frame(
        self,
        session_id: str,
        frame_data: bytes,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a video frame and return multi-person pose detection results.

        Args:
            session_id: Session identifier
            frame_data: JPEG image bytes from browser

        Returns:
            Detection results as dict with multi-person poses, or None if processing failed
        """
        try:
            # Decode JPEG to numpy array
            image = Image.open(io.BytesIO(frame_data))
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            logger.debug(f"Session {session_id}: received {len(frame_data)} bytes, decoded to {frame.shape}")

            # Get detector for this session
            detector = await self.get_detector(session_id)
            logger.debug(f"RTMPose detector initialized: {detector.is_initialized}")

            # Increment frame count
            async with self._lock:
                self._frame_counts[session_id] += 1
                frame_number = self._frame_counts[session_id]

            # Detect multiple persons using ThreadPoolExecutor (non-blocking)
            loop = asyncio.get_event_loop()
            multi_result = await loop.run_in_executor(
                self._executor,
                detector.detect_multi,
                frame
            )
            logger.debug(f"Frame #{frame_number}: detected {multi_result.num_persons} person(s)")

            # Convert multi-person results to API format
            poses_list: List[Dict[str, Any]] = []
            max_persons = 3  # Limit to 3 persons for frontend display

            for i, result in enumerate(multi_result.poses[:max_persons]):
                if result.detected:
                    # Convert landmarks to list format
                    keypoints = [
                        [lm.x, lm.y, lm.z, lm.visibility]
                        for lm in result.landmarks
                    ] if result.landmarks else None

                    # Convert angles to dict
                    angles = result.angles.to_dict() if result.angles else None

                    pose_data = {
                        "person_id": i,
                        "timestamp": result.timestamp,
                        "detected": True,
                        "keypoints": keypoints,
                        "angles": angles,
                        "pose_type": result.pose_type.value,
                        "confidence": result.confidence,
                    }
                    poses_list.append(pose_data)
                    logger.debug(f"Person {i}: confidence={result.confidence:.3f}, pose_type={result.pose_type.value}")

            # Multi-person poses data structure
            poses_data = {
                "timestamp": time.time(),
                "num_persons": len(poses_list),
                "poses": poses_list,
            }

            # Keep legacy single-person `pose` field for backward compatibility
            primary_pose: Optional[Dict[str, Any]] = None
            if poses_list:
                primary_pose = poses_list[0]
            else:
                primary_pose = {
                    "timestamp": time.time(),
                    "detected": False,
                    "confidence": 0.0,
                }

            return {
                "session_id": session_id,
                "frame_number": frame_number,
                "timestamp": time.time(),
                "poses": poses_data,  # Multi-person data
                "pose": primary_pose,  # Backward compatible single-person
            }

        except Exception as e:
            logger.error(f"Frame processing error: {e}", exc_info=True)
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
        # Shutdown thread pool
        self._executor.shutdown(wait=False)


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
    Process audio data from browser using Doubao Streaming ASR (bigmodel_async).

    使用火山引擎豆包大模型进行流式语音识别。
    适配 bigmodel_async 优化模式：发送和接收完全解耦。
    """

    def __init__(self) -> None:
        """Initialize audio processor."""
        from ...perception.doubao_asr_engine import DoubaoConfig

        self._sessions: Dict[str, Any] = {}  # session_id -> DoubaoStreamingSession
        self._result_callbacks: Dict[str, Any] = {}  # session_id -> callback
        self._lock = asyncio.Lock()
        self._config = DoubaoConfig()

        # 检查配置
        if self._config.validate():
            logger.info("DoubaoASR configured (bigmodel_async mode)")
        else:
            logger.warning("DoubaoASR config incomplete, check DOUBAO_APP_ID and DOUBAO_ACCESS_TOKEN")

    async def start_session(
        self,
        session_id: str,
        on_result: Optional[Any] = None,
    ) -> bool:
        """
        Start ASR session for audio processing.

        Args:
            session_id: Session identifier
            on_result: Callback function (text, is_final) -> None

        Returns:
            True if session started successfully
        """
        from ...perception.doubao_asr_engine import DoubaoStreamingSession

        async with self._lock:
            if session_id in self._sessions:
                return True

            if not self._config.validate():
                logger.error("Cannot create ASR session: config invalid")
                return False

            session = DoubaoStreamingSession(self._config, on_result=on_result)
            if await session.start():
                self._sessions[session_id] = session
                self._result_callbacks[session_id] = on_result
                logger.info(f"Started ASR streaming session for {session_id}")
                return True
            else:
                logger.error(f"Failed to start ASR streaming session for {session_id}")
                return False

    async def send_audio(
        self,
        session_id: str,
        audio_data: bytes,
        is_last: bool = False,
    ) -> bool:
        """
        Send audio data to ASR.

        Args:
            session_id: Session identifier
            audio_data: PCM audio bytes (16-bit, mono, 16kHz)
            is_last: Whether this is the last audio chunk

        Returns:
            True if sent successfully
        """
        session = self._sessions.get(session_id)
        if not session:
            if not await self.start_session(session_id):
                return False
            session = self._sessions.get(session_id)

        if not session:
            return False

        try:
            await session.send_audio(audio_data, is_last=is_last)
            return True
        except Exception as e:
            logger.error(f"Error sending audio to ASR: {e}", exc_info=True)
            return False

    def get_current_text(self, session_id: str) -> str:
        """Get current accumulated text (non-blocking)."""
        session = self._sessions.get(session_id)
        if session:
            return session.get_current_text()
        return ""

    async def finalize_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Send last packet and wait for final result."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        try:
            await session.send_audio(b"", is_last=True)

            for _ in range(50):  # 最多等待5秒
                if session.is_finished:
                    break
                await asyncio.sleep(0.1)

            final_text = session.get_current_text()
            return {"text": final_text, "is_final": True} if final_text else None
        except Exception as e:
            logger.error(f"Error finalizing ASR session: {e}", exc_info=True)
            return None

    async def cleanup_session(self, session_id: str) -> Optional[str]:
        """Release resources for a session."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            self._result_callbacks.pop(session_id, None)

        if session:
            final_text = await session.stop()
            logger.info(f"Cleaned up ASR session {session_id}")
            return final_text
        return None

    async def cleanup_all(self) -> None:
        """Release all ASR resources."""
        async with self._lock:
            for session in self._sessions.values():
                await session.stop()
            self._sessions.clear()
            self._result_callbacks.clear()


# Global audio processor
audio_processor = AudioProcessor()


@router.websocket("/ws/audio/{session_id}")
async def websocket_audio(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for receiving audio data from browser.

    适配 bigmodel_async 模式：发送和接收完全解耦。

    Protocol:
    - Client sends: Binary (PCM 16-bit, mono, 16kHz audio bytes)
    - Server responds: JSON with ASR results (when available)

    Response format:
    {
        "type": "asr_result",
        "data": {
            "session_id": "...",
            "text": "识别的文字",
            "is_final": false
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

    # 结果发送队列
    result_queue: asyncio.Queue = asyncio.Queue()

    # 定义回调函数 - 当ASR有结果时调用
    def on_asr_result(text: str, is_final: bool):
        try:
            result_queue.put_nowait({
                "text": text,
                "is_final": is_final,
                "session_id": session_id,
            })
        except Exception:
            pass

    # 启动ASR会话
    asr_started = await audio_processor.start_session(session_id, on_result=on_asr_result)

    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "data": {
            "session_id": session_id,
            "message": "Ready to receive audio data",
            "asr_enabled": asr_started,
        },
        "timestamp": time.time(),
    })

    # 结果发送任务
    async def result_sender():
        """独立任务：将ASR结果发送给客户端."""
        try:
            while True:
                try:
                    result = await asyncio.wait_for(result_queue.get(), timeout=0.5)
                    await websocket.send_json({
                        "type": "asr_result",
                        "data": result,
                        "timestamp": time.time(),
                    })
                    await ws_manager.broadcast(
                        session_id,
                        WSMessage(type="asr", data=result),
                    )
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    # 启动结果发送任务
    sender_task = asyncio.create_task(result_sender())

    try:
        while True:
            # Receive audio data (binary)
            data = await websocket.receive()

            # Check for disconnect
            if data.get("type") == "websocket.disconnect":
                break

            if "bytes" in data:
                # 发送音频数据 (fire and forget)
                audio_data = data["bytes"]
                await audio_processor.send_audio(session_id, audio_data)

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
                        final_result = await audio_processor.finalize_session(session_id)
                        if final_result:
                            await websocket.send_json({
                                "type": "asr_final",
                                "data": final_result,
                                "timestamp": time.time(),
                            })
                        break
                    elif cmd == "get_text":
                        current_text = audio_processor.get_current_text(session_id)
                        await websocket.send_json({
                            "type": "asr_current",
                            "data": {"text": current_text},
                            "timestamp": time.time(),
                        })

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON"},
                        "timestamp": time.time(),
                    })

    except WebSocketDisconnect:
        pass
    finally:
        # 取消结果发送任务
        sender_task.cancel()
        try:
            await sender_task
        except asyncio.CancelledError:
            pass

        # Cleanup ASR for this session
        await audio_processor.cleanup_session(session_id)
