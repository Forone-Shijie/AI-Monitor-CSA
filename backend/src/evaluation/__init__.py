"""
Evaluation Module - Scoring engines and report generation.

This module provides:

Scorers:
    - PoseScorer: Body posture evaluation (30% weight)
    - ActionScorer: SOP timing compliance (40% weight)
    - CommunicationScorer: Speech and terminology (30% weight)

Evaluator:
    - Evaluator: Combined multi-dimensional scoring

Report Generation:
    - ReportGenerator: LLM-powered training reports
    - TrainingReport: Complete report data structure

Usage:
    from src.evaluation import Evaluator, ReportGenerator

    # Evaluate performance
    evaluator = Evaluator()
    result = evaluator.evaluate(
        session_id="session_001",
        scenario_id="brace_position",
        pose_data=pose_result,
        sop_result=sop_result,
        comm_result=comm_result,
    )

    # Generate report
    generator = ReportGenerator()
    report = generator.generate(
        evaluation=result,
        trainee_name="张三",
    )
"""

from .action_scorer import (
    ActionCompliance,
    ActionScore,
    ActionScorer,
    ActionScoreResult,
)
from .communication_scorer import (
    AspectScore,
    CommunicationAspect,
    CommunicationScorer,
    CommunicationScoreResult,
)
from .evaluator import (
    DimensionScore,
    EvaluationResult,
    EvaluationWeights,
    Evaluator,
)
from .pose_scorer import (
    AngleScore,
    CategoryScore,
    PoseScorer,
    PoseScoreResult,
    PostureCategory,
)
from .report_generator import (
    ImprovementSuggestion,
    LLMProvider,
    MockLLMProvider,
    OpenAIProvider,
    ReportGenerator,
    TrainingReport,
)

__all__ = [
    # Pose Scorer
    "PoseScorer",
    "PoseScoreResult",
    "PostureCategory",
    "CategoryScore",
    "AngleScore",
    # Action Scorer
    "ActionScorer",
    "ActionScoreResult",
    "ActionScore",
    "ActionCompliance",
    # Communication Scorer
    "CommunicationScorer",
    "CommunicationScoreResult",
    "CommunicationAspect",
    "AspectScore",
    # Evaluator
    "Evaluator",
    "EvaluationResult",
    "EvaluationWeights",
    "DimensionScore",
    # Report Generator
    "ReportGenerator",
    "TrainingReport",
    "ImprovementSuggestion",
    "LLMProvider",
    "MockLLMProvider",
    "OpenAIProvider",
]
