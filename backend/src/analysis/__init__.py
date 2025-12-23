"""
Analysis Module - Pose Analysis, SOP Compliance, and Multi-modal Sync.

This module provides:

Pose Analysis:
    - PoseAnalyzer: Joint angle calculation and pose analysis
    - BracePositionDetector: Brace/impact position compliance detection

SOP Analysis:
    - SOPAnalyzer: Standard Operating Procedure compliance analysis
    - Synchronizer: Multi-modal data alignment
    - ScenarioTriggerDetector: Scenario trigger detection

Communication Analysis:
    - CommunicationAnalyzer: Speech terminology and timing analysis

Usage:
    from src.analysis import PoseAnalyzer, SOPAnalyzer, Synchronizer

    # Analyze pose
    analyzer = PoseAnalyzer()
    analysis = analyzer.analyze(pose_result)

    # Check SOP compliance
    sop = SOPAnalyzer("config/sop_rules.yaml")
    sop.start_scenario("brace_position")
    sop.record_action("ACT_001", "按压呼叫按钮")
    result = sop.analyze()

    # Synchronize multi-modal data
    sync = Synchronizer()
    sync.add_pose(timestamp, pose)
    sync.add_asr(timestamp, asr)
    frame = sync.get_synced_frame(timestamp)
"""

from .brace_position_detector import (
    ArmPosition,
    BodyPartStatus,
    BracePositionDetector,
    BracePositionResult,
    HeadPosition,
)
from .communication_analyzer import (
    CommunicationAnalysisResult,
    CommunicationAnalyzer,
    CommunicationEvent,
    ResponseTiming,
    ResponseType,
    TerminologyCategory,
    TerminologyMatch,
)
from .pose_analyzer import (
    AngleDeviation,
    PoseAnalysisResult,
    PoseAnalyzer,
    PoseStability,
    SymmetryAnalysis,
)
from .scenario_trigger import (
    ScenarioTriggerDetector,
    TriggerEvent,
    TriggerSource,
)
from .sop_analyzer import (
    ActionEvent,
    ComplianceStatus,
    SOPAnalysisResult,
    SOPAnalyzer,
    SOPScenario,
    SOPStep,
    StepCompliance,
    TriggerType,
)
from .synchronizer import (
    DataType,
    SyncedFrame,
    Synchronizer,
    TimestampedData,
)

__all__ = [
    # Pose Analyzer
    "PoseAnalyzer",
    "PoseAnalysisResult",
    "AngleDeviation",
    "SymmetryAnalysis",
    "PoseStability",
    # Brace Position
    "BracePositionDetector",
    "BracePositionResult",
    "BodyPartStatus",
    "HeadPosition",
    "ArmPosition",
    # Communication Analyzer
    "CommunicationAnalyzer",
    "CommunicationAnalysisResult",
    "CommunicationEvent",
    "TerminologyMatch",
    "TerminologyCategory",
    "ResponseType",
    "ResponseTiming",
    # SOP Analyzer
    "SOPAnalyzer",
    "SOPAnalysisResult",
    "SOPScenario",
    "SOPStep",
    "StepCompliance",
    "ActionEvent",
    "ComplianceStatus",
    "TriggerType",
    # Synchronizer
    "Synchronizer",
    "SyncedFrame",
    "TimestampedData",
    "DataType",
    # Scenario Trigger
    "ScenarioTriggerDetector",
    "TriggerEvent",
    "TriggerSource",
]
