"""
Evaluation Routes - API endpoints for evaluation and reports.

Endpoints:
- GET /evaluation/{session_id} - Get evaluation result
- POST /evaluation/{session_id}/run - Run evaluation
- GET /reports - List reports
- GET /reports/{session_id} - Get report
- POST /reports/{session_id}/generate - Generate report
- GET /reports/{session_id}/export - Export report
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from ..schemas import (
    DimensionScoreData,
    ErrorResponse,
    EvaluationData,
    EvaluationResponse,
    ReportData,
    ReportListResponse,
    ReportResponse,
    SuggestionData,
)
from ..session_manager import session_manager

router = APIRouter(tags=["Evaluation"])


# =============================================================================
# Evaluation Endpoints
# =============================================================================


@router.get(
    "/evaluation/{session_id}",
    response_model=EvaluationResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get evaluation result",
    description="Get evaluation result for a completed session",
)
async def get_evaluation(session_id: str) -> EvaluationResponse:
    """Get evaluation result for a session."""
    session_data = session_manager.get_session_data(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_data.evaluation_result:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not available for this session",
        )

    result = session_data.evaluation_result

    # Convert to response format
    dimension_scores = {}
    for dim, ds in result.get("dimension_scores", {}).items():
        dimension_scores[dim] = DimensionScoreData(
            dimension=ds.get("dimension", dim),
            score=ds.get("score", 0),
            weight=ds.get("weight", 0),
            weighted_score=ds.get("weighted_score", 0),
            grade=ds.get("grade", ""),
            feedback=ds.get("feedback", []),
        )

    data = EvaluationData(
        session_id=session_id,
        scenario_id=result.get("scenario_id", ""),
        scenario_name=result.get("scenario_name", ""),
        total_score=result.get("total_score", 0),
        grade=result.get("grade", ""),
        pose_score=result.get("pose_score", 0),
        action_score=result.get("action_score", 0),
        communication_score=result.get("communication_score", 0),
        dimension_scores=dimension_scores,
        strengths=result.get("strengths", []),
        improvements=result.get("improvements", []),
        summary=result.get("summary", ""),
    )

    return EvaluationResponse(
        success=True,
        message="Evaluation retrieved",
        data=data,
    )


@router.post(
    "/evaluation/{session_id}/run",
    response_model=EvaluationResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Run evaluation",
    description="Run evaluation for a session",
)
async def run_evaluation(session_id: str) -> EvaluationResponse:
    """Run evaluation for a session."""
    from src.evaluation import Evaluator

    session_data = session_manager.get_session_data(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if session has data
    if not session_data.pose_history and not session_data.action_history:
        raise HTTPException(
            status_code=400,
            detail="Session has no monitoring data for evaluation",
        )

    try:
        evaluator = Evaluator()

        # Prepare data for evaluation
        pose_data = session_data.pose_history[-1] if session_data.pose_history else None
        pose_history = session_data.pose_history if len(session_data.pose_history) > 1 else None

        # Run evaluation
        result = evaluator.evaluate(
            session_id=session_id,
            scenario_id=session_data.scenario_id,
            scenario_name=session_data.scenario_name,
            pose_data=pose_data,
            pose_history=pose_history,
        )

        # Store result
        result_dict = result.to_dict()
        session_manager.set_evaluation_result(session_id, result_dict)

        # Convert to response
        dimension_scores = {}
        for dim, ds in result.dimension_scores.items():
            dimension_scores[dim] = DimensionScoreData(
                dimension=ds.dimension,
                score=ds.score,
                weight=ds.weight,
                weighted_score=ds.weighted_score,
                grade=ds.grade,
                feedback=ds.feedback,
            )

        data = EvaluationData(
            session_id=session_id,
            scenario_id=result.scenario_id,
            scenario_name=result.scenario_name,
            total_score=result.total_score,
            grade=result.grade,
            pose_score=result.pose_score.total_score if result.pose_score else 0,
            action_score=result.action_score.total_score if result.action_score else 0,
            communication_score=result.communication_score.total_score if result.communication_score else 0,
            dimension_scores=dimension_scores,
            strengths=result.strengths,
            improvements=result.improvements,
            summary=result.summary,
        )

        return EvaluationResponse(
            success=True,
            message="Evaluation completed",
            data=data,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


# =============================================================================
# Report Endpoints
# =============================================================================


@router.get(
    "/reports",
    response_model=ReportListResponse,
    summary="List reports",
    description="Get list of generated reports",
)
async def list_reports(
    trainee_id: Optional[str] = Query(None, description="Filter by trainee"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
) -> ReportListResponse:
    """List generated reports."""
    # Get sessions with reports
    sessions = session_manager.list_sessions(trainee_id=trainee_id, limit=limit)

    reports = []
    for session in sessions:
        session_data = session_manager.get_session_data(session.session_id)
        if session_data and session_data.report:
            report = session_data.report
            # Extract nested data from TrainingReport.to_dict() format
            session_info = report.get("session", {})
            scores = report.get("scores", {})
            reports.append(
                ReportData(
                    report_id=report.get("report_id", ""),
                    generated_at=report.get("generated_at", ""),
                    session_id=session.session_id,
                    trainee_id=session.trainee_id,
                    trainee_name=session.trainee_name,
                    scenario_id=session.scenario_id,
                    scenario_name=session.scenario_name,
                    session_date=session_info.get("date", ""),
                    duration_seconds=session_info.get("duration_seconds", session.duration_seconds),
                    total_score=scores.get("total", 0),
                    grade=scores.get("grade", ""),
                    pose_score=scores.get("pose", 0),
                    action_score=scores.get("action", 0),
                    communication_score=scores.get("communication", 0),
                    suggestions=[
                        SuggestionData(**s) for s in report.get("suggestions", [])
                    ],
                    ai_summary=report.get("ai_summary", ""),
                    ai_configured=report.get("ai_configured", False),
                    ai_provider=report.get("ai_provider", ""),
                    ai_notice=report.get("ai_notice", ""),
                    strengths=report.get("strengths", []),
                    improvements=report.get("improvements", []),
                )
            )

    return ReportListResponse(
        success=True,
        message="Reports retrieved",
        data=reports,
        total=len(reports),
    )


@router.get(
    "/reports/demo/{report_type}",
    response_model=ReportResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get demo report",
    description="Get preset demo report (perfect or improvement)",
)
async def get_demo_report(report_type: str) -> ReportResponse:
    """Get preset demo report for demonstration purposes."""
    import json
    from pathlib import Path

    if report_type not in ("perfect", "improvement"):
        raise HTTPException(
            status_code=404,
            detail="Demo report type must be 'perfect' or 'improvement'",
        )

    # Determine file path
    base_path = Path(__file__).parent.parent.parent.parent  # backend/
    demo_file = base_path / "data" / "demo_reports" / f"{report_type}_report.json"

    if not demo_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Demo report file not found: {demo_file}",
        )

    with open(demo_file, "r", encoding="utf-8") as f:
        report = json.load(f)

    # Convert to ReportData format
    session_info = report.get("session", {})
    trainee_info = report.get("trainee", {})
    scores = report.get("scores", {})

    data = ReportData(
        report_id=report.get("report_id", ""),
        generated_at=report.get("generated_at", ""),
        session_id=session_info.get("id", ""),
        trainee_id=trainee_info.get("id", ""),
        trainee_name=trainee_info.get("name", ""),
        scenario_id=session_info.get("scenario_id", ""),
        scenario_name=session_info.get("scenario_name", ""),
        session_date=session_info.get("date", ""),
        duration_seconds=session_info.get("duration_seconds", 0),
        total_score=scores.get("total", 0),
        grade=scores.get("grade", ""),
        pose_score=scores.get("pose", 0),
        action_score=scores.get("action", 0),
        communication_score=scores.get("communication", 0),
        suggestions=[SuggestionData(**s) for s in report.get("suggestions", [])],
        ai_summary=report.get("ai_summary", ""),
        ai_configured=report.get("ai_configured", False),
        ai_provider=report.get("ai_provider", ""),
        ai_notice=report.get("ai_notice", ""),
        strengths=report.get("strengths", []),
        improvements=report.get("improvements", []),
    )

    return ReportResponse(
        success=True,
        message=f"Demo report ({report_type}) retrieved",
        data=data,
    )


@router.get(
    "/reports/{session_id}",
    response_model=ReportResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get report",
    description="Get report for a session",
)
async def get_report(session_id: str) -> ReportResponse:
    """Get report for a session."""
    session_data = session_manager.get_session_data(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_data.report:
        raise HTTPException(
            status_code=404,
            detail="Report not available for this session",
        )

    report = session_data.report
    session = session_data.to_info()

    # Extract nested data from TrainingReport.to_dict() format
    session_info = report.get("session", {})
    scores = report.get("scores", {})

    data = ReportData(
        report_id=report.get("report_id", ""),
        generated_at=report.get("generated_at", ""),
        session_id=session.session_id,
        trainee_id=session.trainee_id,
        trainee_name=session.trainee_name,
        scenario_id=session.scenario_id,
        scenario_name=session.scenario_name,
        session_date=session_info.get("date", ""),
        duration_seconds=session_info.get("duration_seconds", session.duration_seconds),
        total_score=scores.get("total", 0),
        grade=scores.get("grade", ""),
        pose_score=scores.get("pose", 0),
        action_score=scores.get("action", 0),
        communication_score=scores.get("communication", 0),
        suggestions=[
            SuggestionData(**s) for s in report.get("suggestions", [])
        ],
        ai_summary=report.get("ai_summary", ""),
        ai_configured=report.get("ai_configured", False),
        ai_provider=report.get("ai_provider", ""),
        ai_notice=report.get("ai_notice", ""),
        strengths=report.get("strengths", []),
        improvements=report.get("improvements", []),
    )

    return ReportResponse(
        success=True,
        message="Report retrieved",
        data=data,
    )


@router.post(
    "/reports/{session_id}/generate",
    response_model=ReportResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Generate report",
    description="Generate training report for a session",
)
async def generate_report(session_id: str) -> ReportResponse:
    """Generate report for a session."""
    from src.evaluation import Evaluator, ReportGenerator

    session_data = session_manager.get_session_data(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Run evaluation first if not available
    if not session_data.evaluation_result:
        if not session_data.pose_history and not session_data.action_history:
            raise HTTPException(
                status_code=400,
                detail="Session has no data for report generation",
            )

        evaluator = Evaluator()
        pose_data = session_data.pose_history[-1] if session_data.pose_history else None

        eval_result = evaluator.evaluate(
            session_id=session_id,
            scenario_id=session_data.scenario_id,
            scenario_name=session_data.scenario_name,
            pose_data=pose_data,
        )
        session_manager.set_evaluation_result(session_id, eval_result.to_dict())
    else:
        # Reconstruct evaluation result
        from src.evaluation import EvaluationResult
        eval_result = None  # Would need reconstruction

    try:
        generator = ReportGenerator()

        # Get session info
        session = session_data.to_info()

        # Generate report
        from src.evaluation import EvaluationResult, EvaluationWeights

        # Simple mock evaluation result for report generation
        class MockEvalResult:
            def __init__(self, data):
                self.session_id = data.get("session_id", session_id)
                self.scenario_id = data.get("scenario_id", session.scenario_id)
                self.scenario_name = data.get("scenario_name", session.scenario_name)
                self.total_score = data.get("total_score", 0)
                self.grade = data.get("grade", "")
                self.strengths = data.get("strengths", [])
                self.improvements = data.get("improvements", [])
                self.summary = data.get("summary", "")
                self.pose_score = None
                self.action_score = None
                self.communication_score = None

        eval_data = session_data.evaluation_result or {}
        mock_eval = MockEvalResult(eval_data)

        report = generator.generate(
            evaluation=mock_eval,
            trainee_id=session.trainee_id,
            trainee_name=session.trainee_name,
            session_date=session.created_at.strftime("%Y-%m-%d"),
            duration_seconds=session.duration_seconds,
        )

        # Store report
        report_dict = report.to_dict()
        session_manager.set_report(session_id, report_dict)

        # Convert to response
        data = ReportData(
            report_id=report.report_id,
            generated_at=report.generated_at,
            session_id=session.session_id,
            trainee_id=session.trainee_id,
            trainee_name=session.trainee_name,
            scenario_id=session.scenario_id,
            scenario_name=session.scenario_name,
            session_date=report.session_date,
            duration_seconds=report.duration_seconds,
            total_score=report.total_score,
            grade=report.grade,
            pose_score=report.pose_score,
            action_score=report.action_score,
            communication_score=report.communication_score,
            suggestions=[
                SuggestionData(
                    category=s.category,
                    priority=s.priority,
                    issue=s.issue,
                    suggestion=s.suggestion,
                    example=s.example,
                )
                for s in report.suggestions
            ],
            ai_summary=report.ai_summary,
            ai_configured=report.ai_configured,
            ai_provider=report.ai_provider,
            ai_notice=report.ai_notice,
            strengths=report.strengths,
            improvements=report.improvements,
        )

        return ReportResponse(
            success=True,
            message="Report generated",
            data=data,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(e)}",
        )


@router.get(
    "/reports/{session_id}/export",
    response_class=PlainTextResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Export report",
    description="Export report as Markdown",
)
async def export_report(
    session_id: str,
    format: str = Query("markdown", description="Export format"),
) -> PlainTextResponse:
    """Export report."""
    from src.evaluation import ReportGenerator, TrainingReport

    session_data = session_manager.get_session_data(session_id)

    if not session_data or not session_data.report:
        raise HTTPException(status_code=404, detail="Report not found")

    report_dict = session_data.report
    session = session_data.to_info()

    # Reconstruct report object
    report = TrainingReport(
        report_id=report_dict.get("report_id", ""),
        generated_at=report_dict.get("generated_at", ""),
        trainee_id=session.trainee_id,
        trainee_name=session.trainee_name,
        session_id=session.session_id,
        scenario_id=session.scenario_id,
        scenario_name=session.scenario_name,
        session_date=report_dict.get("session_date", ""),
        duration_seconds=session.duration_seconds,
        total_score=report_dict.get("total_score", 0),
        grade=report_dict.get("grade", ""),
        pose_score=report_dict.get("pose_score", 0),
        action_score=report_dict.get("action_score", 0),
        communication_score=report_dict.get("communication_score", 0),
        ai_summary=report_dict.get("ai_summary", ""),
        strengths=report_dict.get("strengths", []),
        improvements=report_dict.get("improvements", []),
    )

    generator = ReportGenerator()
    markdown = generator._generate_markdown(report)

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="report_{session_id}.md"'
        },
    )
