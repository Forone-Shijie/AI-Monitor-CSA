"""
Report Generator - Generates evaluation reports with LLM-powered suggestions.

Creates comprehensive training reports including:
- Score summaries
- Detailed analysis
- AI-generated improvement suggestions
- Export to various formats
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .evaluator import EvaluationResult


@dataclass
class ImprovementSuggestion:
    """A single improvement suggestion."""

    category: str  # pose, action, communication
    priority: int  # 1=high, 2=medium, 3=low
    issue: str
    suggestion: str
    example: Optional[str] = None


@dataclass
class TrainingReport:
    """Complete training evaluation report."""

    # Report metadata
    report_id: str
    generated_at: str
    report_version: str = "1.0"

    # Trainee info
    trainee_id: str = ""
    trainee_name: str = ""

    # Session info
    session_id: str = ""
    scenario_id: str = ""
    scenario_name: str = ""
    session_date: str = ""
    duration_seconds: float = 0.0

    # Evaluation results
    evaluation: Optional[EvaluationResult] = None

    # Scores summary
    total_score: float = 0.0
    grade: str = ""
    pose_score: float = 0.0
    action_score: float = 0.0
    communication_score: float = 0.0

    # AI suggestions
    suggestions: List[ImprovementSuggestion] = field(default_factory=list)
    ai_summary: str = ""
    ai_configured: bool = False
    ai_provider: str = ""
    ai_notice: str = ""

    # Detailed feedback
    strengths: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "report_version": self.report_version,
            "trainee": {
                "id": self.trainee_id,
                "name": self.trainee_name,
            },
            "session": {
                "id": self.session_id,
                "scenario_id": self.scenario_id,
                "scenario_name": self.scenario_name,
                "date": self.session_date,
                "duration_seconds": self.duration_seconds,
            },
            "scores": {
                "total": self.total_score,
                "grade": self.grade,
                "pose": self.pose_score,
                "action": self.action_score,
                "communication": self.communication_score,
            },
            "suggestions": [
                {
                    "category": s.category,
                    "priority": s.priority,
                    "issue": s.issue,
                    "suggestion": s.suggestion,
                    "example": s.example,
                }
                for s in self.suggestions
            ],
            "ai_summary": self.ai_summary,
            "ai_configured": self.ai_configured,
            "ai_provider": self.ai_provider,
            "ai_notice": self.ai_notice,
            "strengths": self.strengths,
            "improvements": self.improvements,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if LLM is available."""
        pass


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response: Optional[str] = None) -> None:
        """Initialize mock provider."""
        self._response = response
        self._available = True

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate mock response."""
        if self._response:
            return self._response

        # Generate template-based response
        return self._generate_template_response(prompt)

    def _generate_template_response(self, prompt: str) -> str:
        """Generate a template-based response."""
        if "姿态" in prompt or "pose" in prompt.lower():
            return (
                "根据姿态评估结果，建议：\n"
                "1. 注意保持躯干与大腿的角度在45度左右\n"
                "2. 头部应低垂，双手交叉抱头\n"
                "3. 双脚平放地面，膝盖弯曲约90度"
            )
        elif "动作" in prompt or "action" in prompt.lower():
            return (
                "根据动作时序评估结果，建议：\n"
                "1. 提高动作反应速度，在触发后5秒内完成\n"
                "2. 按照规定顺序执行每个步骤\n"
                "3. 多进行模拟训练以提升熟练度"
            )
        elif "沟通" in prompt or "communication" in prompt.lower():
            return (
                "根据沟通评估结果，建议：\n"
                "1. 使用标准术语，如「防冲击姿势」「保持镇静」\n"
                "2. 语音清晰，语速适中\n"
                "3. 及时响应教员指令"
            )
        else:
            return (
                "综合评估建议：\n"
                "1. 继续保持良好的训练习惯\n"
                "2. 针对薄弱环节进行针对性练习\n"
                "3. 定期回顾训练视频进行自我改进"
            )

    def is_available(self) -> bool:
        """Check availability."""
        return self._available

    def set_available(self, available: bool) -> None:
        """Set availability for testing."""
        self._available = available


class DisabledLLMProvider(LLMProvider):
    """LLM provider that is explicitly disabled."""

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Return empty response when disabled."""
        return ""

    def is_available(self) -> bool:
        """Always unavailable."""
        return False


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (or from env OPENAI_API_KEY)
            model: Model to use
            base_url: Optional custom base URL
        """
        self._api_key = api_key or _get_env_value(["LLM_API_KEY", "OPENAI_API_KEY"])
        self._model = model or _get_env_value(["LLM_MODEL", "OPENAI_MODEL"]) or "gpt-3.5-turbo"
        self._base_url = base_url or _get_env_value(["LLM_BASE_URL", "OPENAI_BASE_URL"])
        self._client = None

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text using OpenAI API."""
        if not self.is_available():
            return ""

        try:
            import openai

            if self._client is None:
                self._client = openai.OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                )

            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一位专业的航空乘务员培训评估专家。"
                            "请根据培训评估结果，提供专业、具体、可操作的改进建议。"
                            "使用中文回复。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.7,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            print(f"OpenAI API error: {e}")
            return ""

    def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        if not self._api_key:
            return False
        try:
            import openai  # noqa: F401
        except Exception:
            return False
        return True


def _get_env_value(keys: List[str]) -> Optional[str]:
    """Return the first non-empty environment value from keys."""
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    return None


def _build_llm_provider_from_env() -> Tuple[LLMProvider, str, bool]:
    """Create an LLM provider based on environment variables."""
    provider = (os.environ.get("LLM_PROVIDER") or "auto").strip().lower()
    api_key = _get_env_value(["LLM_API_KEY", "OPENAI_API_KEY"])
    base_url = _get_env_value(["LLM_BASE_URL", "OPENAI_BASE_URL"])
    model = _get_env_value(["LLM_MODEL", "OPENAI_MODEL"])

    if provider in ("openai", "openai_compatible", "compatible"):
        llm = OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
        return llm, "openai_compatible", llm.is_available()
    if provider in ("mock", "template"):
        return MockLLMProvider(), "mock", False
    if provider in ("none", "disabled", "off"):
        return DisabledLLMProvider(), "disabled", False

    if api_key:
        llm = OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
        return llm, "openai_compatible", llm.is_available()

    return DisabledLLMProvider(), "disabled", False


class ReportGenerator:
    """
    Report generator with LLM-powered suggestions.

    Generates comprehensive training reports including scores,
    analysis, and AI-generated improvement suggestions.

    Usage:
        generator = ReportGenerator()

        # Generate report from evaluation
        report = generator.generate(
            evaluation=eval_result,
            trainee_id="T001",
            trainee_name="张三",
        )

        # Export to JSON
        json_str = report.to_json()

        # Get AI suggestions
        suggestions = generator.generate_suggestions(eval_result)
    """

    SUGGESTION_PROMPT_TEMPLATE = """
基于以下培训评估结果，请提供3-5条具体的改进建议：

场景: {scenario_name}
总分: {total_score:.1f}分 ({grade})

姿态评分: {pose_score:.1f}分
- 反馈: {pose_feedback}

动作评分: {action_score:.1f}分
- 反馈: {action_feedback}

沟通评分: {comm_score:.1f}分
- 反馈: {comm_feedback}

请针对得分较低的方面，提供具体、可操作的改进建议。每条建议包含：
1. 问题描述
2. 改进方法
3. 示例或标准（如适用）
"""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        use_llm: bool = True,
    ) -> None:
        """
        Initialize report generator.

        Args:
            llm_provider: LLM provider for AI suggestions
            use_llm: Whether to use LLM for suggestions
        """
        if llm_provider is None:
            provider, name, configured = _build_llm_provider_from_env()
        else:
            provider = llm_provider
            name, configured = self._describe_provider(provider)

        self._llm_provider = provider
        self._ai_provider = name
        self._ai_configured = configured
        self._use_llm = use_llm

    def set_llm_provider(self, provider: LLMProvider) -> None:
        """Set LLM provider."""
        self._llm_provider = provider
        name, configured = self._describe_provider(provider)
        self._ai_provider = name
        self._ai_configured = configured

    def _describe_provider(self, provider: LLMProvider) -> Tuple[str, bool]:
        """Return provider name and configured status."""
        if isinstance(provider, MockLLMProvider):
            return "mock", False
        if isinstance(provider, DisabledLLMProvider):
            return "disabled", False
        if isinstance(provider, OpenAIProvider):
            return "openai_compatible", provider.is_available()
        return provider.__class__.__name__.lower(), provider.is_available()

    def _build_ai_notice(self, include_ai_suggestions: bool) -> str:
        """Return a user-facing notice when AI is not configured."""
        if not include_ai_suggestions or not self._use_llm:
            return ""
        if self._ai_configured:
            return ""
        if self._ai_provider == "mock":
            return "AI未配置：当前使用Mock模板（未接入在线大模型）"
        if self._ai_provider == "disabled":
            return (
                "AI未配置：请设置 LLM_PROVIDER=openai，并配置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL"
            )
        return "AI未配置：请检查 LLM_PROVIDER 和 API Key 配置"

    def generate(
        self,
        evaluation: EvaluationResult,
        trainee_id: str = "",
        trainee_name: str = "",
        session_date: Optional[str] = None,
        duration_seconds: float = 0.0,
        include_ai_suggestions: bool = True,
    ) -> TrainingReport:
        """
        Generate complete training report.

        Args:
            evaluation: Evaluation result
            trainee_id: Trainee identifier
            trainee_name: Trainee name
            session_date: Session date
            duration_seconds: Session duration
            include_ai_suggestions: Whether to include AI suggestions

        Returns:
            TrainingReport
        """
        now = datetime.now()
        report_id = f"RPT-{now.strftime('%Y%m%d%H%M%S')}-{evaluation.session_id[:8]}"

        # Extract scores
        pose_score = (
            evaluation.pose_score.total_score if evaluation.pose_score else 0.0
        )
        action_score = (
            evaluation.action_score.total_score if evaluation.action_score else 0.0
        )
        comm_score = (
            evaluation.communication_score.total_score
            if evaluation.communication_score
            else 0.0
        )

        # Generate suggestions
        suggestions = []
        ai_summary = ""

        if include_ai_suggestions and self._use_llm:
            suggestions = self.generate_suggestions(evaluation)
            ai_summary = self._generate_ai_summary(evaluation)

        ai_notice = self._build_ai_notice(include_ai_suggestions)

        # Combine feedback
        strengths = evaluation.strengths.copy()
        improvements = evaluation.improvements.copy()

        return TrainingReport(
            report_id=report_id,
            generated_at=now.isoformat(),
            trainee_id=trainee_id,
            trainee_name=trainee_name,
            session_id=evaluation.session_id,
            scenario_id=evaluation.scenario_id,
            scenario_name=evaluation.scenario_name,
            session_date=session_date or now.strftime("%Y-%m-%d"),
            duration_seconds=duration_seconds,
            evaluation=evaluation,
            total_score=evaluation.total_score,
            grade=evaluation.grade,
            pose_score=pose_score,
            action_score=action_score,
            communication_score=comm_score,
            suggestions=suggestions,
            ai_summary=ai_summary,
            ai_configured=self._ai_configured,
            ai_provider=self._ai_provider,
            ai_notice=ai_notice,
            strengths=strengths,
            improvements=improvements,
        )

    def generate_suggestions(
        self,
        evaluation: EvaluationResult,
    ) -> List[ImprovementSuggestion]:
        """
        Generate improvement suggestions.

        Args:
            evaluation: Evaluation result

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Rule-based suggestions
        suggestions.extend(self._generate_rule_based_suggestions(evaluation))

        # LLM-based suggestions
        if self._use_llm and self._llm_provider.is_available():
            llm_suggestions = self._generate_llm_suggestions(evaluation)
            suggestions.extend(llm_suggestions)

        # Sort by priority
        suggestions.sort(key=lambda x: x.priority)

        return suggestions[:5]  # Limit to top 5

    def _generate_rule_based_suggestions(
        self,
        evaluation: EvaluationResult,
    ) -> List[ImprovementSuggestion]:
        """Generate rule-based suggestions."""
        suggestions = []

        # Pose suggestions
        if evaluation.pose_score:
            pose = evaluation.pose_score
            if pose.total_score < 70:
                suggestions.append(
                    ImprovementSuggestion(
                        category="pose",
                        priority=1,
                        issue="姿态标准分偏低",
                        suggestion="建议多练习标准防冲击姿势，注意躯干弯曲角度和手部位置",
                        example="躯干前倾约45度，双手交叉抱头，膝盖弯曲90度",
                    )
                )
            if pose.stability_score and pose.stability_score < 80:
                suggestions.append(
                    ImprovementSuggestion(
                        category="pose",
                        priority=2,
                        issue="姿态保持稳定性不足",
                        suggestion="练习保持姿势的持久性，避免在规定时间内出现大幅度移动",
                    )
                )

        # Action suggestions
        if evaluation.action_score:
            action = evaluation.action_score
            if action.total_score < 70:
                suggestions.append(
                    ImprovementSuggestion(
                        category="action",
                        priority=1,
                        issue="动作时效分偏低",
                        suggestion="提高对触发信号的反应速度，熟悉SOP流程顺序",
                        example="听到指令后应在5秒内开始执行相应动作",
                    )
                )
            if not action.sequence_correct:
                suggestions.append(
                    ImprovementSuggestion(
                        category="action",
                        priority=1,
                        issue="动作序列不完整",
                        suggestion="确保按照SOP规定完成所有必需动作",
                    )
                )

        # Communication suggestions
        if evaluation.communication_score:
            comm = evaluation.communication_score
            if comm.total_score < 70:
                suggestions.append(
                    ImprovementSuggestion(
                        category="communication",
                        priority=2,
                        issue="沟通协同分偏低",
                        suggestion="练习标准术语的使用，提高响应速度",
                        example="使用「防冲击姿势」「保持镇静」等标准用语",
                    )
                )
            if comm.missed_terms:
                suggestions.append(
                    ImprovementSuggestion(
                        category="communication",
                        priority=2,
                        issue="标准术语使用不全",
                        suggestion=f"建议熟悉并使用以下术语: {', '.join(comm.missed_terms[:3])}",
                    )
                )

        return suggestions

    def _generate_llm_suggestions(
        self,
        evaluation: EvaluationResult,
    ) -> List[ImprovementSuggestion]:
        """Generate LLM-based suggestions."""
        prompt = self._build_suggestion_prompt(evaluation)
        response = self._llm_provider.generate(prompt, max_tokens=500)

        if not response:
            return []

        # Parse response into suggestions
        return self._parse_llm_response(response)

    def _build_suggestion_prompt(self, evaluation: EvaluationResult) -> str:
        """Build prompt for LLM."""
        pose_feedback = ""
        action_feedback = ""
        comm_feedback = ""

        if evaluation.pose_score:
            pose_feedback = "; ".join(evaluation.pose_score.improvements[:3])
        if evaluation.action_score:
            action_feedback = "; ".join(evaluation.action_score.improvements[:3])
        if evaluation.communication_score:
            comm_feedback = "; ".join(evaluation.communication_score.improvements[:3])

        return self.SUGGESTION_PROMPT_TEMPLATE.format(
            scenario_name=evaluation.scenario_name,
            total_score=evaluation.total_score,
            grade=evaluation.grade,
            pose_score=(
                evaluation.pose_score.total_score if evaluation.pose_score else 0
            ),
            pose_feedback=pose_feedback or "无",
            action_score=(
                evaluation.action_score.total_score if evaluation.action_score else 0
            ),
            action_feedback=action_feedback or "无",
            comm_score=(
                evaluation.communication_score.total_score
                if evaluation.communication_score
                else 0
            ),
            comm_feedback=comm_feedback or "无",
        )

    def _parse_llm_response(
        self,
        response: str,
    ) -> List[ImprovementSuggestion]:
        """Parse LLM response into suggestions."""
        suggestions = []

        # Simple parsing - split by numbered items
        lines = response.strip().split("\n")
        current_suggestion = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for numbered item
            if line[0].isdigit() and (line[1] == "." or line[1] == "、"):
                if current_suggestion:
                    suggestions.append(current_suggestion)

                # Determine category
                category = "general"
                if "姿态" in line or "姿势" in line:
                    category = "pose"
                elif "动作" in line or "时序" in line:
                    category = "action"
                elif "沟通" in line or "术语" in line or "语音" in line:
                    category = "communication"

                current_suggestion = ImprovementSuggestion(
                    category=category,
                    priority=len(suggestions) + 1,
                    issue=line[2:].strip() if len(line) > 2 else line,
                    suggestion="",
                )
            elif current_suggestion:
                # Add to current suggestion
                if current_suggestion.suggestion:
                    current_suggestion.suggestion += " " + line
                else:
                    current_suggestion.suggestion = line

        if current_suggestion:
            suggestions.append(current_suggestion)

        return suggestions

    def _generate_ai_summary(self, evaluation: EvaluationResult) -> str:
        """Generate AI summary."""
        if not self._llm_provider.is_available():
            return evaluation.summary

        prompt = f"""
请用2-3句话总结以下培训评估结果：

场景: {evaluation.scenario_name}
总分: {evaluation.total_score:.1f}分 ({evaluation.grade})
优点: {', '.join(evaluation.strengths[:3]) or '无'}
待改进: {', '.join(evaluation.improvements[:3]) or '无'}

请给出简洁、鼓励性的总结。
"""

        response = self._llm_provider.generate(prompt, max_tokens=200)
        return response or evaluation.summary

    def export_to_json(
        self,
        report: TrainingReport,
        file_path: str,
    ) -> bool:
        """
        Export report to JSON file.

        Args:
            report: Training report
            file_path: Output file path

        Returns:
            True if successful
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report.to_json())
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False

    def export_to_markdown(
        self,
        report: TrainingReport,
        file_path: str,
    ) -> bool:
        """
        Export report to Markdown file.

        Args:
            report: Training report
            file_path: Output file path

        Returns:
            True if successful
        """
        try:
            md_content = self._generate_markdown(report)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False

    def _generate_markdown(self, report: TrainingReport) -> str:
        """Generate Markdown content."""
        lines = [
            f"# 培训评估报告",
            f"",
            f"**报告编号**: {report.report_id}",
            f"**生成时间**: {report.generated_at}",
            f"",
            f"## 基本信息",
            f"",
            f"| 项目 | 内容 |",
            f"|------|------|",
            f"| 学员姓名 | {report.trainee_name or '-'} |",
            f"| 学员编号 | {report.trainee_id or '-'} |",
            f"| 训练场景 | {report.scenario_name} |",
            f"| 训练日期 | {report.session_date} |",
            f"| 训练时长 | {report.duration_seconds:.0f}秒 |",
            f"",
            f"## 评估结果",
            f"",
            f"### 总体评分: {report.total_score:.1f}分 ({report.grade})",
            f"",
            f"| 维度 | 分数 | 权重 |",
            f"|------|------|------|",
            f"| 姿态标准 | {report.pose_score:.1f} | 30% |",
            f"| 动作时效 | {report.action_score:.1f} | 40% |",
            f"| 沟通协同 | {report.communication_score:.1f} | 30% |",
            f"",
        ]

        if report.strengths:
            lines.extend([
                f"## 优点",
                f"",
            ])
            for s in report.strengths:
                lines.append(f"- {s}")
            lines.append("")

        if report.improvements:
            lines.extend([
                f"## 待改进",
                f"",
            ])
            for s in report.improvements:
                lines.append(f"- {s}")
            lines.append("")

        if report.suggestions:
            lines.extend([
                f"## 改进建议",
                f"",
            ])
            for i, s in enumerate(report.suggestions, 1):
                lines.append(f"### {i}. {s.issue}")
                lines.append(f"")
                lines.append(f"**建议**: {s.suggestion}")
                if s.example:
                    lines.append(f"")
                    lines.append(f"**示例**: {s.example}")
                lines.append("")

        if report.ai_summary:
            lines.extend([
                f"## AI总结",
                f"",
                f"{report.ai_summary}",
                f"",
            ])

        lines.extend([
            f"---",
            f"",
            f"*报告由 CC-SOP Monitor 系统自动生成*",
        ])

        return "\n".join(lines)
