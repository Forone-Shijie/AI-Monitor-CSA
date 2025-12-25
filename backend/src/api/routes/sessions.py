"""
Session Routes - API endpoints for session management.

Endpoints:
- POST /sessions - Create new session
- GET /sessions - List sessions
- GET /sessions/{id} - Get session
- POST /sessions/{id}/start - Start monitoring
- POST /sessions/{id}/stop - Stop monitoring
- DELETE /sessions/{id} - Delete session
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..schemas import (
    ErrorResponse,
    SessionCreate,
    SessionInfo,
    SessionListResponse,
    SessionResponse,
    SessionStartRequest,
    SessionStatus,
    SessionStopRequest,
    SessionUpdate,
)
from ..session_manager import session_manager
from ..monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Create training session",
    description="Create a new training session for a trainee",
)
async def create_session(request: SessionCreate) -> SessionResponse:
    """Create a new training session."""
    try:
        session = session_manager.create_session(
            trainee_id=request.trainee_id,
            trainee_name=request.trainee_name,
            scenario_id=request.scenario_id,
            video_source=request.video_source,
            video_path=request.video_path,
            camera_id=request.camera_id,
        )

        return SessionResponse(
            success=True,
            message="Session created successfully",
            data=session,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List sessions",
    description="Get list of training sessions with optional filtering",
)
async def list_sessions(
    status: Optional[SessionStatus] = Query(None, description="Filter by status"),
    trainee_id: Optional[str] = Query(None, description="Filter by trainee"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
) -> SessionListResponse:
    """List training sessions."""
    sessions = session_manager.list_sessions(
        status=status,
        trainee_id=trainee_id,
        limit=limit,
    )

    return SessionListResponse(
        success=True,
        message="Sessions retrieved",
        data=sessions,
        total=len(sessions),
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get session",
    description="Get training session by ID",
)
async def get_session(session_id: str) -> SessionResponse:
    """Get session by ID."""
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        success=True,
        message="Session retrieved",
        data=session,
    )


@router.put(
    "/{session_id}",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Update session",
    description="Update training session parameters (only allowed when not running)",
)
async def update_session(
    session_id: str,
    request: SessionUpdate,
) -> SessionResponse:
    """Update session parameters."""
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == SessionStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="Cannot update session while running. Please pause or stop the session first.",
        )

    updated = session_manager.update_session(
        session_id=session_id,
        trainee_id=request.trainee_id,
        trainee_name=request.trainee_name,
        scenario_id=request.scenario_id,
        camera_id=request.camera_id,
        audio_device_id=request.audio_device_id,
    )

    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update session")

    return SessionResponse(
        success=True,
        message="Session updated successfully",
        data=updated,
    )


@router.post(
    "/{session_id}/start",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Start monitoring",
    description="Start monitoring for a training session",
)
async def start_session(
    session_id: str,
    request: Optional[SessionStartRequest] = None,
) -> SessionResponse:
    """Start monitoring for a session."""
    trigger_type = request.trigger_type if request else "manual"

    # Get session data for video source config
    session_data = session_manager.get_session_data(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Start session state
    success = session_manager.start_session(session_id, trigger_type)

    if not success:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start session in {session.status} status",
        )

    # Start monitoring service (camera, pose detection, etc.)
    # If user explicitly selected a camera (not default 0), require it to be available
    require_camera = session_data.camera_id != 0
    try:
        await monitoring_service.start(
            session_id=session_id,
            video_source=session_data.video_source,
            video_path=session_data.video_path,
            camera_id=session_data.camera_id,
            require_camera=require_camera,
        )
    except RuntimeError as e:
        # Device not available error
        session_manager.cancel_session(session_id)
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        # If monitoring fails, revert session state
        session_manager.cancel_session(session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start monitoring: {str(e)}",
        )

    session = session_manager.get_session(session_id)

    return SessionResponse(
        success=True,
        message="Monitoring started",
        data=session,
    )


@router.post(
    "/{session_id}/pause",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Pause monitoring",
    description="Pause monitoring for a training session",
)
async def pause_session(session_id: str) -> SessionResponse:
    """Pause monitoring for a session."""
    # Stop monitoring service
    await monitoring_service.stop(session_id)

    success = session_manager.pause_session(session_id)

    if not success:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause session in {session.status} status",
        )

    session = session_manager.get_session(session_id)

    return SessionResponse(
        success=True,
        message="Monitoring paused",
        data=session,
    )


@router.post(
    "/{session_id}/stop",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Stop monitoring",
    description="Stop monitoring and complete the session",
)
async def stop_session(
    session_id: str,
    request: Optional[SessionStopRequest] = None,
) -> SessionResponse:
    """Stop monitoring for a session."""
    generate_report = request.generate_report if request else True

    # Stop monitoring service
    await monitoring_service.stop(session_id)

    success = session_manager.stop_session(session_id, generate_report)

    if not success:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot stop session in {session.status} status",
        )

    # Generate report if requested
    if generate_report:
        try:
            await _generate_session_report(session_id)
        except Exception as e:
            logger.error(f"Failed to generate report for session {session_id}: {e}")
            # Don't fail the stop request if report generation fails

    session = session_manager.get_session(session_id)

    return SessionResponse(
        success=True,
        message="Monitoring stopped" + (" and report generated" if generate_report else ""),
        data=session,
    )


async def _generate_session_report(session_id: str) -> None:
    """Generate evaluation and report for a completed session."""
    from src.evaluation.evaluator import Evaluator, EvaluationResult
    from src.evaluation.report_generator import ReportGenerator

    session_data = session_manager.get_session_data(session_id)
    if not session_data:
        raise ValueError(f"Session {session_id} not found")

    # Calculate duration
    duration_seconds = 0.0
    if session_data.started_at and session_data.ended_at:
        duration_seconds = (session_data.ended_at - session_data.started_at).total_seconds()

    # Create evaluator and evaluate session
    evaluator = Evaluator()

    # Get the latest pose data for evaluation
    pose_data = session_data.pose_history[-1] if session_data.pose_history else None
    brace_result = session_data.brace_history[-1] if session_data.brace_history else None

    eval_result = evaluator.evaluate(
        session_id=session_id,
        scenario_id=session_data.scenario_id,
        scenario_name=session_data.scenario_name,
        pose_data=pose_data,
        pose_history=session_data.pose_history,
        brace_result=brace_result,
    )

    # Store evaluation result
    session_manager.set_evaluation_result(session_id, eval_result.to_dict())

    # Generate report
    generator = ReportGenerator()
    report = generator.generate(
        evaluation=eval_result,
        trainee_id=session_data.trainee_id,
        trainee_name=session_data.trainee_name,
        session_date=session_data.created_at.strftime("%Y-%m-%d"),
        duration_seconds=duration_seconds,
        include_ai_suggestions=True,
    )

    # Store report
    session_manager.set_report(session_id, report.to_dict())

    logger.info(f"Generated report for session {session_id}: score={eval_result.total_score}, grade={eval_result.grade}")


@router.post(
    "/{session_id}/cancel",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Cancel session",
    description="Cancel a training session",
)
async def cancel_session(session_id: str) -> SessionResponse:
    """Cancel a session."""
    # Stop monitoring service if running
    await monitoring_service.stop(session_id)

    success = session_manager.cancel_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_manager.get_session(session_id)

    return SessionResponse(
        success=True,
        message="Session cancelled",
        data=session,
    )


@router.delete(
    "/{session_id}",
    response_model=SessionResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Delete session",
    description="Delete a training session",
)
async def delete_session(session_id: str) -> SessionResponse:
    """Delete a session."""
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_manager.delete_session(session_id)

    return SessionResponse(
        success=True,
        message="Session deleted",
        data=session,
    )


@router.get(
    "/{session_id}/status",
    summary="Get monitoring status",
    description="Get real-time monitoring status for a session",
)
async def get_monitoring_status(session_id: str):
    """Get monitoring status."""
    status = session_manager.get_monitoring_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "message": "Status retrieved",
        "data": status,
    }
