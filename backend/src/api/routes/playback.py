"""
Playback Routes - API endpoints for session playback.

Endpoints:
- GET /playback/{session_id} - Get playback data
- GET /playback/{session_id}/frames - Get frames in range
- GET /playback/{session_id}/timeline - Get timeline events
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..schemas import (
    ASRData,
    ActionData,
    BracePositionData,
    ErrorResponse,
    PlaybackData,
    PlaybackFrame,
    PlaybackResponse,
    PoseData,
)
from ..session_manager import session_manager

router = APIRouter(prefix="/playback", tags=["Playback"])


@router.get(
    "/{session_id}",
    response_model=PlaybackResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get playback data",
    description="Get complete playback data for a session",
)
async def get_playback(
    session_id: str,
    start_frame: int = Query(0, ge=0, description="Start frame number"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum frames"),
) -> PlaybackResponse:
    """Get playback data for a session."""
    session_data = session_manager.get_session_data(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Calculate duration and fps
    duration = 0.0
    if session_data.started_at:
        end = session_data.ended_at or session_data.started_at
        duration = (end - session_data.started_at).total_seconds()

    fps = session_data.fps if session_data.fps > 0 else 30.0

    # Build frames
    frames = []
    total_frames = max(
        len(session_data.pose_history),
        len(session_data.action_history),
        len(session_data.asr_history),
        len(session_data.brace_history),
    )

    # Create frame index
    pose_by_frame = {p.get("frame_number", i): p for i, p in enumerate(session_data.pose_history)}
    action_by_frame = {a.get("frame_number", i): a for i, a in enumerate(session_data.action_history)}
    asr_by_frame = {a.get("frame_number", i): a for i, a in enumerate(session_data.asr_history)}
    brace_by_frame = {b.get("frame_number", i): b for i, b in enumerate(session_data.brace_history)}

    end_frame = min(start_frame + limit, total_frames)

    for frame_num in range(start_frame, end_frame):
        pose = pose_by_frame.get(frame_num)
        action = action_by_frame.get(frame_num)
        asr = asr_by_frame.get(frame_num)
        brace = brace_by_frame.get(frame_num)

        frame = PlaybackFrame(
            frame_number=frame_num,
            timestamp=frame_num / fps,
            pose=PoseData(**pose) if pose else None,
            action=ActionData(**action) if action else None,
            asr=ASRData(**asr) if asr else None,
            brace=BracePositionData(**brace) if brace else None,
        )
        frames.append(frame)

    data = PlaybackData(
        session_id=session_id,
        total_frames=total_frames,
        duration_seconds=duration,
        fps=fps,
        frames=frames,
    )

    return PlaybackResponse(
        success=True,
        message="Playback data retrieved",
        data=data,
    )


@router.get(
    "/{session_id}/frames",
    summary="Get frames in range",
    description="Get specific frames by time range",
)
async def get_frames(
    session_id: str,
    start_time: float = Query(0.0, ge=0, description="Start time in seconds"),
    end_time: Optional[float] = Query(None, description="End time in seconds"),
    data_types: str = Query("pose,action,asr,brace", description="Comma-separated data types"),
):
    """Get frames in time range."""
    session_data = session_manager.get_session_data(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    fps = session_data.fps if session_data.fps > 0 else 30.0
    types = set(data_types.split(","))

    # Calculate frame range
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps) if end_time else len(session_data.pose_history)

    frames = []

    for i, pose in enumerate(session_data.pose_history):
        frame_num = pose.get("frame_number", i)
        if start_frame <= frame_num < end_frame:
            frame_data = {
                "frame_number": frame_num,
                "timestamp": frame_num / fps,
            }

            if "pose" in types:
                frame_data["pose"] = pose

            frames.append(frame_data)

    return {
        "success": True,
        "message": "Frames retrieved",
        "data": {
            "session_id": session_id,
            "start_time": start_time,
            "end_time": end_time or (len(session_data.pose_history) / fps),
            "frame_count": len(frames),
            "frames": frames,
        },
    }


@router.get(
    "/{session_id}/timeline",
    summary="Get timeline events",
    description="Get timeline of events for a session",
)
async def get_timeline(session_id: str):
    """Get timeline events for a session."""
    session_data = session_manager.get_session_data(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build timeline from events
    timeline = []

    # Add session events
    for event in session_data.events:
        timeline.append({
            "type": "event",
            "name": event.get("type"),
            "timestamp": event.get("timestamp"),
            "data": event.get("data"),
        })

    # Add action events
    for action in session_data.action_history:
        timeline.append({
            "type": "action",
            "name": action.get("action_name", action.get("action_id")),
            "timestamp": action.get("timestamp"),
            "confidence": action.get("confidence"),
        })

    # Add ASR events
    for asr in session_data.asr_history:
        if asr.get("is_final", True):
            timeline.append({
                "type": "asr",
                "text": asr.get("text"),
                "timestamp": asr.get("timestamp"),
                "confidence": asr.get("confidence"),
            })

    # Sort by timestamp
    timeline.sort(key=lambda x: x.get("timestamp", 0))

    return {
        "success": True,
        "message": "Timeline retrieved",
        "data": {
            "session_id": session_id,
            "event_count": len(timeline),
            "events": timeline,
        },
    }


@router.get(
    "/{session_id}/summary",
    summary="Get session summary",
    description="Get summary statistics for a session",
)
async def get_summary(session_id: str):
    """Get session summary statistics."""
    session_data = session_manager.get_session_data(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_data.to_info()

    # Calculate statistics
    pose_count = len(session_data.pose_history)
    action_count = len(session_data.action_history)
    asr_count = len(session_data.asr_history)

    # Average confidence
    pose_confidences = [
        p.get("confidence", 0) for p in session_data.pose_history if p.get("confidence")
    ]
    avg_pose_confidence = sum(pose_confidences) / len(pose_confidences) if pose_confidences else 0

    return {
        "success": True,
        "message": "Summary retrieved",
        "data": {
            "session_id": session_id,
            "trainee_name": session.trainee_name,
            "scenario_name": session.scenario_name,
            "status": session.status.value,
            "duration_seconds": session.duration_seconds,
            "statistics": {
                "total_frames": session_data.frame_count,
                "pose_detections": pose_count,
                "action_events": action_count,
                "asr_transcriptions": asr_count,
                "average_fps": session_data.fps,
                "average_pose_confidence": avg_pose_confidence,
            },
            "has_evaluation": session_data.evaluation_result is not None,
            "has_report": session_data.report is not None,
        },
    }
