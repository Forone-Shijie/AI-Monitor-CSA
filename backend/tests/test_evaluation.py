"""
Phase 6 Tests - Evaluation Engine.

Tests for:
- PoseScorer: Posture evaluation
- ActionScorer: SOP timing compliance
- CommunicationScorer: Speech analysis
- Evaluator: Combined scoring
- ReportGenerator: Report generation
"""

import time
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.evaluation import (
    ActionCompliance,
    ActionScore,
    ActionScorer,
    ActionScoreResult,
    AngleScore,
    AspectScore,
    CategoryScore,
    CommunicationAspect,
    CommunicationScorer,
    CommunicationScoreResult,
    DimensionScore,
    EvaluationResult,
    EvaluationWeights,
    Evaluator,
    ImprovementSuggestion,
    LLMProvider,
    MockLLMProvider,
    OpenAIProvider,
    PoseScorer,
    PoseScoreResult,
    PostureCategory,
    ReportGenerator,
    TrainingReport,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_pose_data():
    """Sample pose data for testing."""
    return {
        "angles": {
            "spine_angle": 40.0,
            "head_tilt": -25.0,
            "elbow_angle": 85.0,
            "shoulder_angle": 50.0,
            "knee_angle": 88.0,
            "hip_angle": 95.0,
        }
    }


@pytest.fixture
def sample_sop_result():
    """Sample SOP analysis result for testing."""

    @dataclass
    class MockStep:
        step_id: int
        action_id: str
        action_name: str
        time_limit: float
        required: bool = True

    @dataclass
    class MockStepCompliance:
        step: MockStep
        status: MagicMock
        actual_time: Optional[float] = None
        time_taken: Optional[float] = None
        deviation: float = 0.0

    @dataclass
    class MockSOPResult:
        scenario_id: str
        scenario_name: str
        steps_compliance: List[MockStepCompliance]
        total_time: float
        time_limit: float
        is_compliant: bool

    # Create mock status
    compliant_status = MagicMock()
    compliant_status.value = "compliant"

    timeout_status = MagicMock()
    timeout_status.value = "timeout"

    steps = [
        MockStepCompliance(
            step=MockStep(1, "ACT_001", "弯腰低头", 5.0),
            status=compliant_status,
            actual_time=time.time() + 2.0,
            time_taken=2.0,
            deviation=0.0,
        ),
        MockStepCompliance(
            step=MockStep(2, "ACT_002", "双手抱头", 3.0),
            status=timeout_status,
            actual_time=time.time() + 5.0,
            time_taken=5.0,
            deviation=2.0,
        ),
        MockStepCompliance(
            step=MockStep(3, "ACT_003", "保持姿势", 20.0),
            status=compliant_status,
            actual_time=time.time() + 15.0,
            time_taken=15.0,
            deviation=0.0,
        ),
    ]

    return MockSOPResult(
        scenario_id="brace_position",
        scenario_name="防冲击姿势",
        steps_compliance=steps,
        total_time=20.0,
        time_limit=30.0,
        is_compliant=True,
    )


@pytest.fixture
def sample_comm_result():
    """Sample communication result for testing."""

    @dataclass
    class MockCommResult:
        text: str
        confidence: float
        clarity_score: float
        response_timing: Optional[MagicMock] = None
        terminology_matches: List = None

        def __post_init__(self):
            if self.terminology_matches is None:
                self.terminology_matches = []

    timing = MagicMock()
    timing.response_time = 2.5

    return MockCommResult(
        text="请做好防冲击姿势，低头弯腰，双手抱头",
        confidence=0.92,
        clarity_score=85.0,
        response_timing=timing,
        terminology_matches=["防冲击姿势", "低头弯腰"],
    )


# =============================================================================
# PoseScorer Tests
# =============================================================================


class TestPoseScorer:
    """Tests for PoseScorer."""

    def test_init(self):
        """Test scorer initialization."""
        scorer = PoseScorer()
        assert scorer.scenario == "brace_position"
        assert PostureCategory.TORSO in scorer.weights

    def test_set_scenario(self):
        """Test setting scenario."""
        scorer = PoseScorer()
        scorer.set_scenario("standing")
        assert scorer.scenario == "standing"

    def test_set_weights(self):
        """Test setting weights."""
        scorer = PoseScorer()
        scorer.set_weights({
            PostureCategory.TORSO: 0.5,
            PostureCategory.HEAD: 0.2,
            PostureCategory.ARMS: 0.2,
            PostureCategory.LEGS: 0.1,
        })
        assert scorer.weights[PostureCategory.TORSO] == 0.5

    def test_score_basic(self, sample_pose_data):
        """Test basic pose scoring."""
        scorer = PoseScorer()
        result = scorer.score(sample_pose_data)

        assert isinstance(result, PoseScoreResult)
        assert 0 <= result.total_score <= 100
        assert result.grade in ["A", "B", "C", "D", "F"]

    def test_score_categories(self, sample_pose_data):
        """Test category scoring."""
        scorer = PoseScorer()
        result = scorer.score(sample_pose_data)

        assert PostureCategory.TORSO in result.category_scores
        assert PostureCategory.HEAD in result.category_scores
        assert PostureCategory.ARMS in result.category_scores
        assert PostureCategory.LEGS in result.category_scores

    def test_score_perfect_pose(self):
        """Test scoring perfect pose."""
        scorer = PoseScorer()
        perfect_pose = {
            "angles": {
                "spine_angle": 45.0,  # Exact target
                "head_tilt": -30.0,  # Exact target
                "elbow_angle": 90.0,
                "shoulder_angle": 45.0,
                "knee_angle": 90.0,
                "hip_angle": 90.0,
            }
        }
        result = scorer.score(perfect_pose)
        assert result.total_score >= 90

    def test_score_poor_pose(self):
        """Test scoring poor pose."""
        scorer = PoseScorer()
        poor_pose = {
            "angles": {
                "spine_angle": 0.0,  # Very wrong
                "head_tilt": 30.0,  # Very wrong
                "elbow_angle": 180.0,
                "shoulder_angle": 0.0,
                "knee_angle": 180.0,
                "hip_angle": 180.0,
            }
        }
        result = scorer.score(poor_pose)
        assert result.total_score < 60

    def test_score_with_history(self, sample_pose_data):
        """Test scoring with history."""
        scorer = PoseScorer()
        history = [sample_pose_data] * 10

        result = scorer.score_with_history(history, min_hold_duration=5.0)

        assert result.hold_duration > 0
        assert result.stability_score >= 0

    def test_score_empty_history(self):
        """Test scoring empty history."""
        scorer = PoseScorer()
        result = scorer.score_with_history([])

        assert result.total_score == 0
        assert result.grade == "F"

    def test_add_custom_standard(self):
        """Test adding custom standard."""
        scorer = PoseScorer()
        scorer.add_custom_standard(
            scenario="custom",
            category=PostureCategory.TORSO,
            joint_name="custom_angle",
            target=60.0,
            tolerance=10.0,
        )

        assert "custom" in scorer.SCENARIO_STANDARDS
        assert PostureCategory.TORSO in scorer.SCENARIO_STANDARDS["custom"]

    def test_result_to_dict(self, sample_pose_data):
        """Test result serialization."""
        scorer = PoseScorer()
        result = scorer.score(sample_pose_data)
        result_dict = result.to_dict()

        assert "total_score" in result_dict
        assert "grade" in result_dict
        assert "category_scores" in result_dict

    def test_grade_thresholds(self):
        """Test grade calculation."""
        scorer = PoseScorer()

        # Test each grade threshold
        assert scorer._calculate_grade(95) == "A"
        assert scorer._calculate_grade(85) == "B"
        assert scorer._calculate_grade(75) == "C"
        assert scorer._calculate_grade(65) == "D"
        assert scorer._calculate_grade(55) == "F"


# =============================================================================
# ActionScorer Tests
# =============================================================================


class TestActionScorer:
    """Tests for ActionScorer."""

    def test_init(self):
        """Test scorer initialization."""
        scorer = ActionScorer()
        assert scorer is not None

    def test_score_from_sop_result(self, sample_sop_result):
        """Test scoring from SOP result."""
        scorer = ActionScorer()
        result = scorer.score(sample_sop_result)

        assert isinstance(result, ActionScoreResult)
        assert result.scenario_id == "brace_position"
        assert 0 <= result.total_score <= 100

    def test_score_action_details(self, sample_sop_result):
        """Test action score details."""
        scorer = ActionScorer()
        result = scorer.score(sample_sop_result)

        assert len(result.action_scores) == 3
        assert result.action_scores[0].compliance == ActionCompliance.ON_TIME
        assert result.action_scores[1].compliance == ActionCompliance.DELAYED

    def test_score_completion_rate(self, sample_sop_result):
        """Test completion rate calculation."""
        scorer = ActionScorer()
        result = scorer.score(sample_sop_result)

        assert result.completion_rate == 1.0  # All completed

    def test_score_manual_recording(self):
        """Test manual action recording."""
        scorer = ActionScorer()
        base_time = time.time()

        scorer.set_scenario(
            scenario_id="test",
            scenario_name="Test Scenario",
            steps=[
                {"action_id": "ACT_001", "action_name": "Step 1", "time_limit": 5.0},
                {"action_id": "ACT_002", "action_name": "Step 2", "time_limit": 3.0},
            ],
            trigger_time=base_time,
        )

        scorer.record_action("ACT_001", base_time + 2.0)
        scorer.record_action("ACT_002", base_time + 4.0)

        result = scorer.calculate_score()

        assert result.scenario_id == "test"
        assert len(result.action_scores) == 2

    def test_score_missing_actions(self):
        """Test scoring with missing actions."""
        scorer = ActionScorer()
        base_time = time.time()

        scorer.set_scenario(
            scenario_id="test",
            scenario_name="Test",
            steps=[
                {"action_id": "ACT_001", "action_name": "Step 1", "time_limit": 5.0},
            ],
            trigger_time=base_time,
        )

        # Don't record any actions
        result = scorer.calculate_score()

        assert result.completion_rate == 0.0
        assert result.action_scores[0].compliance == ActionCompliance.MISSING

    def test_score_no_sop_result(self):
        """Test scoring without SOP result."""
        scorer = ActionScorer()
        result = scorer.score(None)

        assert result.total_score == 0
        assert result.grade == "F"

    def test_reset(self):
        """Test reset functionality."""
        scorer = ActionScorer()
        scorer.set_scenario("test", "Test", [], time.time())
        scorer.reset()

        result = scorer.calculate_score()
        assert result.scenario_id == ""

    def test_result_to_dict(self, sample_sop_result):
        """Test result serialization."""
        scorer = ActionScorer()
        result = scorer.score(sample_sop_result)
        result_dict = result.to_dict()

        assert "total_score" in result_dict
        assert "action_scores" in result_dict
        assert "completion_rate" in result_dict


# =============================================================================
# CommunicationScorer Tests
# =============================================================================


class TestCommunicationScorer:
    """Tests for CommunicationScorer."""

    def test_init(self):
        """Test scorer initialization."""
        scorer = CommunicationScorer()
        assert CommunicationAspect.TIMELINESS in scorer._weights

    def test_set_weights(self):
        """Test setting weights."""
        scorer = CommunicationScorer()
        scorer.set_weights({
            CommunicationAspect.TIMELINESS: 0.5,
            CommunicationAspect.TERMINOLOGY: 0.3,
            CommunicationAspect.CLARITY: 0.1,
            CommunicationAspect.COMPLETENESS: 0.1,
        })
        assert scorer._weights[CommunicationAspect.TIMELINESS] == 0.5

    def test_score_basic(self, sample_comm_result):
        """Test basic communication scoring."""
        scorer = CommunicationScorer()
        result = scorer.score(sample_comm_result, scenario="brace_position")

        assert isinstance(result, CommunicationScoreResult)
        assert 0 <= result.total_score <= 100

    def test_score_with_expectations(self, sample_comm_result):
        """Test scoring with expected terms."""
        scorer = CommunicationScorer()
        result = scorer.score_with_expectations(
            sample_comm_result,
            expected_terms=["防冲击姿势", "低头弯腰", "双手抱头"],
            time_limit=5.0,
        )

        assert result.terminology_accuracy > 0
        assert len(result.correct_terms) > 0

    def test_score_timeliness(self, sample_comm_result):
        """Test timeliness scoring."""
        scorer = CommunicationScorer()
        result = scorer.score(sample_comm_result)

        assert CommunicationAspect.TIMELINESS in result.aspect_scores
        assert result.response_time == 2.5

    def test_score_terminology(self, sample_comm_result):
        """Test terminology scoring."""
        scorer = CommunicationScorer()
        result = scorer.score_with_expectations(
            sample_comm_result,
            expected_terms=["防冲击姿势"],
        )

        assert "防冲击姿势" in result.correct_terms

    def test_score_no_expected_terms(self, sample_comm_result):
        """Test scoring without expected terms."""
        scorer = CommunicationScorer()
        result = scorer.score_with_expectations(
            sample_comm_result,
            expected_terms=[],
        )

        assert result.terminology_accuracy == 100.0

    def test_get_scenario_terms(self):
        """Test getting scenario terms."""
        scorer = CommunicationScorer()
        terms = scorer.get_scenario_terms("brace_position")

        assert len(terms) > 0
        assert "防冲击姿势" in terms

    def test_add_scenario_terms(self):
        """Test adding scenario terms."""
        scorer = CommunicationScorer()
        scorer.add_scenario_terms("custom", ["自定义术语"])

        terms = scorer.get_scenario_terms("custom")
        assert "自定义术语" in terms

    def test_result_to_dict(self, sample_comm_result):
        """Test result serialization."""
        scorer = CommunicationScorer()
        result = scorer.score(sample_comm_result)
        result_dict = result.to_dict()

        assert "total_score" in result_dict
        assert "aspect_scores" in result_dict
        assert "clarity_score" in result_dict


# =============================================================================
# Evaluator Tests
# =============================================================================


class TestEvaluator:
    """Tests for Evaluator."""

    def test_init(self):
        """Test evaluator initialization."""
        evaluator = Evaluator()

        assert evaluator.weights.pose == 0.30
        assert evaluator.weights.action == 0.40
        assert evaluator.weights.communication == 0.30

    def test_set_weights(self):
        """Test setting weights."""
        evaluator = Evaluator()
        evaluator.set_weights(pose=0.4, action=0.3, communication=0.3)

        assert evaluator.weights.pose == 0.4

    def test_evaluate_full(
        self, sample_pose_data, sample_sop_result, sample_comm_result
    ):
        """Test full evaluation."""
        evaluator = Evaluator()
        result = evaluator.evaluate(
            session_id="test_session",
            scenario_id="brace_position",
            scenario_name="防冲击姿势",
            pose_data=sample_pose_data,
            sop_result=sample_sop_result,
            comm_result=sample_comm_result,
        )

        assert isinstance(result, EvaluationResult)
        assert result.session_id == "test_session"
        assert result.scenario_id == "brace_position"
        assert 0 <= result.total_score <= 100
        assert result.grade in ["A", "B", "C", "D", "F"]

    def test_evaluate_pose_only(self, sample_pose_data):
        """Test pose-only evaluation."""
        evaluator = Evaluator()
        result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
        )

        assert result.pose_score is not None
        assert result.action_score is None
        assert result.communication_score is None

    def test_evaluate_action_only(self, sample_sop_result):
        """Test action-only evaluation."""
        evaluator = Evaluator()
        result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            sop_result=sample_sop_result,
        )

        assert result.action_score is not None
        assert result.pose_score is None

    def test_evaluate_with_history(self, sample_pose_data):
        """Test evaluation with pose history."""
        evaluator = Evaluator()
        history = [sample_pose_data] * 10

        result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_history=history,
        )

        assert result.pose_score is not None
        assert result.pose_score.hold_duration > 0

    def test_dimension_scores(
        self, sample_pose_data, sample_sop_result, sample_comm_result
    ):
        """Test dimension scores."""
        evaluator = Evaluator()
        result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
            sop_result=sample_sop_result,
            comm_result=sample_comm_result,
        )

        assert "pose" in result.dimension_scores
        assert "action" in result.dimension_scores
        assert "communication" in result.dimension_scores

    def test_feedback_combination(
        self, sample_pose_data, sample_sop_result, sample_comm_result
    ):
        """Test feedback combination."""
        evaluator = Evaluator()
        result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
            sop_result=sample_sop_result,
            comm_result=sample_comm_result,
        )

        # Should have combined feedback
        assert isinstance(result.strengths, list)
        assert isinstance(result.improvements, list)

    def test_summary_generation(
        self, sample_pose_data, sample_sop_result, sample_comm_result
    ):
        """Test summary generation."""
        evaluator = Evaluator()
        result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            scenario_name="防冲击姿势",
            pose_data=sample_pose_data,
            sop_result=sample_sop_result,
            comm_result=sample_comm_result,
        )

        assert result.summary
        assert "防冲击姿势" in result.summary

    def test_result_to_dict(self, sample_pose_data):
        """Test result serialization."""
        evaluator = Evaluator()
        result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
        )
        result_dict = result.to_dict()

        assert "session_id" in result_dict
        assert "total_score" in result_dict
        assert "dimension_scores" in result_dict


# =============================================================================
# EvaluationWeights Tests
# =============================================================================


class TestEvaluationWeights:
    """Tests for EvaluationWeights."""

    def test_default_weights(self):
        """Test default weights."""
        weights = EvaluationWeights()

        assert weights.pose == 0.30
        assert weights.action == 0.40
        assert weights.communication == 0.30

    def test_custom_weights(self):
        """Test custom weights."""
        weights = EvaluationWeights(pose=0.5, action=0.3, communication=0.2)

        assert weights.pose == 0.5
        assert weights.action == 0.3
        assert weights.communication == 0.2

    def test_normalize(self):
        """Test weight normalization."""
        weights = EvaluationWeights(pose=1.0, action=1.0, communication=1.0)
        normalized = weights.normalize()

        total = normalized.pose + normalized.action + normalized.communication
        assert abs(total - 1.0) < 0.01

    def test_to_dict(self):
        """Test conversion to dict."""
        weights = EvaluationWeights()
        weights_dict = weights.to_dict()

        assert "pose" in weights_dict
        assert "action" in weights_dict
        assert "communication" in weights_dict


# =============================================================================
# ReportGenerator Tests
# =============================================================================


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_init(self):
        """Test generator initialization."""
        generator = ReportGenerator()
        assert generator is not None

    def test_init_with_provider(self):
        """Test initialization with LLM provider."""
        provider = MockLLMProvider()
        generator = ReportGenerator(llm_provider=provider)
        assert generator is not None

    def test_generate_report(self, sample_pose_data, sample_sop_result):
        """Test report generation."""
        evaluator = Evaluator()
        eval_result = evaluator.evaluate(
            session_id="test_session",
            scenario_id="brace_position",
            scenario_name="防冲击姿势",
            pose_data=sample_pose_data,
            sop_result=sample_sop_result,
        )

        generator = ReportGenerator()
        report = generator.generate(
            evaluation=eval_result,
            trainee_id="T001",
            trainee_name="张三",
        )

        assert isinstance(report, TrainingReport)
        assert report.trainee_name == "张三"
        assert report.scenario_name == "防冲击姿势"

    def test_generate_suggestions(self, sample_pose_data):
        """Test suggestion generation."""
        evaluator = Evaluator()
        eval_result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
        )

        generator = ReportGenerator()
        suggestions = generator.generate_suggestions(eval_result)

        assert isinstance(suggestions, list)
        for s in suggestions:
            assert isinstance(s, ImprovementSuggestion)

    def test_report_to_json(self, sample_pose_data):
        """Test report JSON export."""
        evaluator = Evaluator()
        eval_result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
        )

        generator = ReportGenerator()
        report = generator.generate(eval_result)

        json_str = report.to_json()
        assert isinstance(json_str, str)
        assert "scores" in json_str
        assert "total" in json_str

    def test_report_to_dict(self, sample_pose_data):
        """Test report dict export."""
        evaluator = Evaluator()
        eval_result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
        )

        generator = ReportGenerator()
        report = generator.generate(eval_result)

        report_dict = report.to_dict()
        assert "report_id" in report_dict
        assert "scores" in report_dict

    def test_export_to_markdown(self, sample_pose_data, tmp_path):
        """Test Markdown export."""
        evaluator = Evaluator()
        eval_result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
        )

        generator = ReportGenerator()
        report = generator.generate(
            eval_result,
            trainee_name="测试学员",
        )

        md_path = tmp_path / "report.md"
        success = generator.export_to_markdown(report, str(md_path))

        assert success
        assert md_path.exists()

        content = md_path.read_text()
        assert "培训评估报告" in content
        assert "测试学员" in content


# =============================================================================
# MockLLMProvider Tests
# =============================================================================


class TestMockLLMProvider:
    """Tests for MockLLMProvider."""

    def test_generate(self):
        """Test text generation."""
        provider = MockLLMProvider()
        response = provider.generate("Test prompt")

        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_with_custom_response(self):
        """Test with custom response."""
        provider = MockLLMProvider(response="Custom response")
        response = provider.generate("Any prompt")

        assert response == "Custom response"

    def test_is_available(self):
        """Test availability check."""
        provider = MockLLMProvider()
        assert provider.is_available()

    def test_set_available(self):
        """Test setting availability."""
        provider = MockLLMProvider()
        provider.set_available(False)
        assert not provider.is_available()

    def test_template_response_pose(self):
        """Test template response for pose."""
        provider = MockLLMProvider()
        response = provider.generate("分析姿态评估结果")

        assert "姿态" in response or "角度" in response

    def test_template_response_action(self):
        """Test template response for action."""
        provider = MockLLMProvider()
        response = provider.generate("分析动作时序")

        assert "动作" in response or "反应" in response


# =============================================================================
# Integration Tests
# =============================================================================


class TestEvaluationIntegration:
    """Integration tests for evaluation workflow."""

    def test_full_evaluation_workflow(
        self, sample_pose_data, sample_sop_result, sample_comm_result
    ):
        """Test complete evaluation workflow."""
        # 1. Create evaluator
        evaluator = Evaluator()

        # 2. Perform evaluation
        eval_result = evaluator.evaluate(
            session_id="integration_test",
            scenario_id="brace_position",
            scenario_name="防冲击姿势",
            pose_data=sample_pose_data,
            sop_result=sample_sop_result,
            comm_result=sample_comm_result,
        )

        # 3. Generate report
        generator = ReportGenerator()
        report = generator.generate(
            evaluation=eval_result,
            trainee_id="T001",
            trainee_name="张三",
            duration_seconds=30.0,
        )

        # Verify results
        assert eval_result.total_score > 0
        assert report.report_id.startswith("RPT-")
        assert report.total_score == eval_result.total_score
        assert len(report.suggestions) > 0 or len(report.improvements) > 0

    def test_evaluation_with_custom_weights(self, sample_pose_data, sample_sop_result):
        """Test evaluation with custom weights."""
        evaluator = Evaluator()
        evaluator.set_weights(pose=0.5, action=0.4, communication=0.1)

        result = evaluator.evaluate(
            session_id="test",
            scenario_id="brace_position",
            pose_data=sample_pose_data,
            sop_result=sample_sop_result,
        )

        assert result.weights.pose == 0.5
        assert result.dimension_scores["pose"].weight == 0.5


# =============================================================================
# Data Class Tests
# =============================================================================


class TestDataClasses:
    """Tests for data classes."""

    def test_angle_score(self):
        """Test AngleScore dataclass."""
        score = AngleScore(
            joint_name="knee_angle",
            target_angle=90.0,
            actual_angle=85.0,
            deviation=5.0,
            score=90.0,
            feedback="膝盖角度良好",
        )

        assert score.joint_name == "knee_angle"
        assert score.deviation == 5.0

    def test_category_score(self):
        """Test CategoryScore dataclass."""
        score = CategoryScore(
            category=PostureCategory.TORSO,
            score=85.0,
            weight=0.3,
            weighted_score=25.5,
        )

        assert score.category == PostureCategory.TORSO
        assert score.weighted_score == 25.5

    def test_action_score(self):
        """Test ActionScore dataclass."""
        score = ActionScore(
            action_id="ACT_001",
            action_name="弯腰低头",
            compliance=ActionCompliance.ON_TIME,
            time_limit=5.0,
            actual_time=3.0,
            time_deviation=0.0,
            score=100.0,
        )

        assert score.compliance == ActionCompliance.ON_TIME

    def test_improvement_suggestion(self):
        """Test ImprovementSuggestion dataclass."""
        suggestion = ImprovementSuggestion(
            category="pose",
            priority=1,
            issue="姿态偏差",
            suggestion="调整躯干角度",
            example="躯干前倾45度",
        )

        assert suggestion.priority == 1
        assert suggestion.example is not None

    def test_dimension_score(self):
        """Test DimensionScore dataclass."""
        score = DimensionScore(
            dimension="pose",
            score=85.0,
            weight=0.3,
            weighted_score=25.5,
            grade="B",
        )

        assert score.dimension == "pose"
        assert score.grade == "B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
