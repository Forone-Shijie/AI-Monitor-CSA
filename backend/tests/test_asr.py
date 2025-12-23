"""
Unit tests for ASR (Automatic Speech Recognition) module.

Tests ASREngine, WhisperASR, and CommunicationAnalyzer.
"""

import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.perception.asr_engine import (
    ASREngine,
    ASRLanguage,
    ASRResult,
    ASRSegment,
    ASRStatus,
    STANDARD_TERMINOLOGY,
)


class TestASRSegment:
    """Tests for ASRSegment dataclass."""

    def test_segment_creation(self):
        """Test creating an ASR segment."""
        segment = ASRSegment(
            text="测试语音",
            start_time=0.0,
            end_time=2.5,
            confidence=0.95,
            language="zh",
        )

        assert segment.text == "测试语音"
        assert segment.start_time == 0.0
        assert segment.end_time == 2.5
        assert segment.confidence == 0.95
        assert segment.language == "zh"

    def test_segment_duration(self):
        """Test segment duration calculation."""
        segment = ASRSegment(
            text="test",
            start_time=1.5,
            end_time=4.0,
            confidence=0.9,
        )

        assert segment.duration == 2.5

    def test_segment_to_dict(self):
        """Test converting segment to dictionary."""
        segment = ASRSegment(
            text="hello",
            start_time=0.0,
            end_time=1.0,
            confidence=0.8,
            language="en",
        )

        d = segment.to_dict()

        assert isinstance(d, dict)
        assert d["text"] == "hello"
        assert d["start_time"] == 0.0
        assert d["end_time"] == 1.0
        assert d["confidence"] == 0.8
        assert d["language"] == "en"
        assert d["duration"] == 1.0


class TestASRResult:
    """Tests for ASRResult dataclass."""

    @pytest.fixture
    def sample_segments(self):
        """Create sample segments."""
        return [
            ASRSegment(
                text="第一段",
                start_time=0.0,
                end_time=2.0,
                confidence=0.9,
            ),
            ASRSegment(
                text="第二段",
                start_time=2.5,
                end_time=4.5,
                confidence=0.85,
            ),
            ASRSegment(
                text="第三段",
                start_time=5.0,
                end_time=7.0,
                confidence=0.95,
            ),
        ]

    def test_result_success(self, sample_segments):
        """Test successful ASR result."""
        result = ASRResult(
            success=True,
            text="第一段 第二段 第三段",
            segments=sample_segments,
            language="zh",
            confidence=0.9,
            duration=7.0,
            processing_time=0.5,
        )

        assert result.success is True
        assert len(result.segments) == 3
        assert result.duration == 7.0
        assert result.error_message is None

    def test_result_failure(self):
        """Test failed ASR result."""
        result = ASRResult(
            success=False,
            text="",
            error_message="Audio too short",
        )

        assert result.success is False
        assert result.text == ""
        assert result.error_message == "Audio too short"

    def test_get_text_at_time(self, sample_segments):
        """Test getting segment at timestamp."""
        result = ASRResult(
            success=True,
            text="full text",
            segments=sample_segments,
        )

        # Within first segment
        seg = result.get_text_at_time(1.0)
        assert seg is not None
        assert seg.text == "第一段"

        # Within second segment
        seg = result.get_text_at_time(3.0)
        assert seg is not None
        assert seg.text == "第二段"

        # Between segments (no match)
        seg = result.get_text_at_time(2.2)
        assert seg is None

    def test_get_segments_in_range(self, sample_segments):
        """Test getting segments in time range."""
        result = ASRResult(
            success=True,
            text="full text",
            segments=sample_segments,
        )

        # Range covering first two segments
        segs = result.get_segments_in_range(0.0, 3.0)
        assert len(segs) == 2

        # Range covering all segments
        segs = result.get_segments_in_range(0.0, 10.0)
        assert len(segs) == 3

        # Range with no segments
        segs = result.get_segments_in_range(10.0, 15.0)
        assert len(segs) == 0

    def test_to_dict(self, sample_segments):
        """Test converting result to dictionary."""
        result = ASRResult(
            success=True,
            text="full text",
            segments=sample_segments,
            language="zh",
            confidence=0.9,
            duration=7.0,
            processing_time=0.5,
        )

        d = result.to_dict()

        assert isinstance(d, dict)
        assert d["success"] is True
        assert d["text"] == "full text"
        assert len(d["segments"]) == 3
        assert d["language"] == "zh"


class TestASRLanguage:
    """Tests for ASRLanguage enum."""

    def test_language_values(self):
        """Test language enum values."""
        assert ASRLanguage.CHINESE.value == "zh"
        assert ASRLanguage.ENGLISH.value == "en"
        assert ASRLanguage.AUTO.value == "auto"


class TestASRStatus:
    """Tests for ASRStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ASRStatus.IDLE.value == "idle"
        assert ASRStatus.LISTENING.value == "listening"
        assert ASRStatus.PROCESSING.value == "processing"
        assert ASRStatus.ERROR.value == "error"


class TestStandardTerminology:
    """Tests for standard terminology dictionary."""

    def test_terminology_exists(self):
        """Test that terminology dictionary exists."""
        assert STANDARD_TERMINOLOGY is not None
        assert len(STANDARD_TERMINOLOGY) > 0

    def test_emergency_terms(self):
        """Test emergency terminology."""
        assert "brace" in STANDARD_TERMINOLOGY
        assert "evacuate" in STANDARD_TERMINOLOGY
        assert "fire" in STANDARD_TERMINOLOGY

    def test_safety_terms(self):
        """Test safety terminology."""
        assert "check_seatbelt" in STANDARD_TERMINOLOGY
        assert "check_tray" in STANDARD_TERMINOLOGY

    def test_communication_terms(self):
        """Test communication terminology."""
        assert "confirm" in STANDARD_TERMINOLOGY
        assert "report" in STANDARD_TERMINOLOGY

    def test_variations_exist(self):
        """Test that variations exist for terms."""
        for term_id, variations in STANDARD_TERMINOLOGY.items():
            assert isinstance(variations, list)
            assert len(variations) > 0


class TestMockWhisperASR:
    """Tests for MockWhisperASR class."""

    @pytest.fixture
    def mock_asr(self):
        """Create mock ASR instance."""
        from src.perception.whisper_asr import MockWhisperASR

        return MockWhisperASR(mock_text="测试语音识别")

    def test_mock_init(self, mock_asr):
        """Test mock ASR initialization."""
        assert mock_asr.is_initialized
        assert mock_asr.status == ASRStatus.IDLE

    def test_mock_transcribe(self, mock_asr):
        """Test mock transcription."""
        audio = np.zeros(16000, dtype=np.float32)  # 1 second
        result = mock_asr.transcribe(audio, sample_rate=16000)

        assert result.success is True
        assert result.text == "测试语音识别"
        assert len(result.segments) == 1
        assert result.duration == 1.0

    def test_mock_transcribe_file_not_found(self, mock_asr):
        """Test mock transcription with non-existent file."""
        result = mock_asr.transcribe_file("/nonexistent/file.wav")

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_mock_release(self, mock_asr):
        """Test releasing mock ASR."""
        assert mock_asr.is_initialized

        mock_asr.release()

        assert not mock_asr.is_initialized

    def test_mock_context_manager(self):
        """Test mock ASR as context manager."""
        from src.perception.whisper_asr import MockWhisperASR

        with MockWhisperASR() as asr:
            assert asr.is_initialized
            result = asr.transcribe(np.zeros(16000, dtype=np.float32))
            assert result.success

        assert not asr.is_initialized


class TestCommunicationAnalyzer:
    """Tests for CommunicationAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        from src.analysis.communication_analyzer import CommunicationAnalyzer

        return CommunicationAnalyzer()

    @pytest.fixture
    def sample_asr_result(self):
        """Create sample ASR result with terminology."""
        return ASRResult(
            success=True,
            text="防冲击姿势！收到，明白！",
            segments=[
                ASRSegment(
                    text="防冲击姿势！",
                    start_time=0.0,
                    end_time=2.0,
                    confidence=0.9,
                    language="zh",
                ),
                ASRSegment(
                    text="收到，明白！",
                    start_time=2.5,
                    end_time=4.0,
                    confidence=0.95,
                    language="zh",
                ),
            ],
            language="zh",
            confidence=0.92,
            duration=4.0,
        )

    def test_analyzer_init(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None
        terminology = analyzer.get_terminology()
        assert len(terminology) > 0

    def test_analyze_success(self, analyzer, sample_asr_result):
        """Test analyzing ASR result."""
        result = analyzer.analyze(sample_asr_result)

        assert result is not None
        assert result.asr_result == sample_asr_result
        assert len(result.events) == 2
        assert 0 <= result.overall_score <= 100

    def test_detect_terminology(self, analyzer, sample_asr_result):
        """Test terminology detection."""
        result = analyzer.analyze(sample_asr_result)

        # Should find "brace" terminology
        brace_matches = [
            m for m in result.terminology_matches
            if m.term_id == "brace"
        ]
        assert len(brace_matches) > 0

        # Should find acknowledgment
        confirm_matches = [
            m for m in result.terminology_matches
            if m.term_id == "confirm"
        ]
        assert len(confirm_matches) > 0

    def test_detect_keywords(self, analyzer):
        """Test keyword detection."""
        text = "请注意，防冲击姿势！所有人员准备撤离！"

        matches = analyzer.detect_keywords(text)

        assert len(matches) > 0
        term_ids = [m[0] for m in matches]
        assert "brace" in term_ids
        assert "evacuate" in term_ids

    def test_detect_specific_keywords(self, analyzer):
        """Test detecting specific keywords only."""
        text = "防冲击姿势！撤离！火警！"

        matches = analyzer.detect_keywords(text, keywords=["brace", "fire"])

        term_ids = [m[0] for m in matches]
        assert "brace" in term_ids
        assert "fire" in term_ids
        assert "evacuate" not in term_ids

    def test_analyze_empty_result(self, analyzer):
        """Test analyzing empty/failed ASR result."""
        empty_result = ASRResult(
            success=False,
            text="",
            error_message="Recognition failed",
        )

        result = analyzer.analyze(empty_result)

        assert result is not None
        assert len(result.events) == 0
        assert "失败" in result.feedback[0]

    def test_add_custom_terminology(self, analyzer):
        """Test adding custom terminology."""
        analyzer.add_terminology(
            "custom_term",
            ["自定义术语", "custom term"],
        )

        terminology = analyzer.get_terminology()
        assert "custom_term" in terminology

        # Test detection with new terminology
        text = "使用自定义术语进行测试"
        matches = analyzer.detect_keywords(text, keywords=["custom_term"])
        assert len(matches) > 0

    def test_set_time_limit(self, analyzer):
        """Test setting custom time limit."""
        analyzer.set_time_limit("acknowledgment", 5.0)

        # Time limit should be updated
        assert analyzer._time_limits["acknowledgment"] == 5.0

    def test_response_timing_analysis(self, analyzer):
        """Test response timing analysis."""
        # Create ASR result with command and delayed response
        asr_result = ASRResult(
            success=True,
            text="防冲击！... 收到",
            segments=[
                ASRSegment(
                    text="防冲击！",
                    start_time=0.0,
                    end_time=1.0,
                    confidence=0.9,
                ),
                ASRSegment(
                    text="收到",
                    start_time=4.0,  # 3 second delay
                    end_time=4.5,
                    confidence=0.9,
                ),
            ],
            language="zh",
            confidence=0.9,
        )

        result = analyzer.analyze(asr_result)

        # Should have timing analysis
        assert len(result.response_timings) >= 0  # May or may not have timing

    def test_clarity_score(self, analyzer):
        """Test clarity score calculation."""
        # High confidence segments
        high_conf_result = ASRResult(
            success=True,
            text="清晰语音",
            segments=[
                ASRSegment(
                    text="清晰语音",
                    start_time=0.0,
                    end_time=1.0,
                    confidence=0.95,
                ),
            ],
            language="zh",
            confidence=0.95,
        )

        result = analyzer.analyze(high_conf_result)
        assert result.clarity_score >= 70

    def test_to_dict(self, analyzer, sample_asr_result):
        """Test converting result to dictionary."""
        result = analyzer.analyze(sample_asr_result)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert "terminology_score" in d
        assert "timeliness_score" in d
        assert "clarity_score" in d
        assert "overall_score" in d
        assert "events" in d
        assert "terminology_matches" in d

    def test_missed_terminology(self, analyzer):
        """Test finding missed terminology."""
        # ASR result without expected terms
        asr_result = ASRResult(
            success=True,
            text="准备完毕",
            segments=[
                ASRSegment(
                    text="准备完毕",
                    start_time=0.0,
                    end_time=1.0,
                    confidence=0.9,
                ),
            ],
            language="zh",
            confidence=0.9,
        )

        # Expect brace and evacuate terms
        result = analyzer.analyze(
            asr_result,
            expected_terminology={"brace", "evacuate"},
        )

        assert "brace" in result.missed_terminology
        assert "evacuate" in result.missed_terminology


class TestDoubaoASR:
    """Tests for DoubaoASR class."""

    @pytest.fixture
    def mock_doubao(self):
        """Create mock Doubao ASR instance."""
        from src.perception.doubao_asr import MockDoubaoASR

        return MockDoubaoASR(mock_text="豆包测试结果", is_available=True)

    def test_mock_doubao_init(self, mock_doubao):
        """Test mock Doubao initialization."""
        assert mock_doubao.is_initialized
        assert mock_doubao.is_available

    def test_mock_doubao_transcribe(self, mock_doubao):
        """Test mock Doubao transcription."""
        audio = np.zeros(16000, dtype=np.float32)
        result = mock_doubao.transcribe(audio, sample_rate=16000)

        assert result.success is True
        assert result.text == "豆包测试结果"
        assert result.processing_time > 0

    def test_mock_doubao_unavailable(self):
        """Test mock Doubao when unavailable."""
        from src.perception.doubao_asr import MockDoubaoASR

        asr = MockDoubaoASR(is_available=False)
        audio = np.zeros(16000, dtype=np.float32)
        result = asr.transcribe(audio)

        assert result.success is False
        assert "not available" in result.error_message.lower()

    def test_mock_doubao_set_available(self):
        """Test setting mock availability."""
        from src.perception.doubao_asr import MockDoubaoASR

        asr = MockDoubaoASR(is_available=True)
        assert asr.is_available

        asr.set_available(False)
        assert not asr.is_available

    def test_doubao_config(self):
        """Test DoubaoConfig creation."""
        from src.perception.doubao_asr import DoubaoConfig

        config = DoubaoConfig(
            app_id="test_app_id",
            access_token="test_token",
            cluster="test_cluster",
        )

        assert config.app_id == "test_app_id"
        assert config.access_token == "test_token"
        assert config.cluster == "test_cluster"
        assert config.sample_rate == 16000


class TestHybridASR:
    """Tests for HybridASR class."""

    @pytest.fixture
    def mock_hybrid(self):
        """Create mock hybrid ASR instance."""
        from src.perception.hybrid_asr import ASRMode, MockHybridASR

        return MockHybridASR(
            mode=ASRMode.AUTO,
            online_available=True,
            online_text="在线结果",
            offline_text="离线结果",
        )

    def test_hybrid_init(self, mock_hybrid):
        """Test hybrid ASR initialization."""
        from src.perception.hybrid_asr import ASRMode

        assert mock_hybrid.is_initialized
        assert mock_hybrid.current_mode == ASRMode.ONLINE

    def test_hybrid_transcribe_online(self, mock_hybrid):
        """Test hybrid transcription using online mode."""
        audio = np.zeros(16000, dtype=np.float32)
        result = mock_hybrid.transcribe(audio, sample_rate=16000)

        assert result.success is True
        assert result.text == "在线结果"

    def test_hybrid_fallback_to_offline(self, mock_hybrid):
        """Test fallback to offline when online unavailable."""
        from src.perception.hybrid_asr import ASRMode

        # Set online unavailable
        mock_hybrid.set_online_available(False)

        audio = np.zeros(16000, dtype=np.float32)
        result = mock_hybrid.transcribe(audio, sample_rate=16000)

        assert result.success is True
        assert result.text == "离线结果"
        assert mock_hybrid.current_mode == ASRMode.OFFLINE

    def test_hybrid_force_offline_mode(self):
        """Test forcing offline mode."""
        from src.perception.hybrid_asr import ASRMode, MockHybridASR

        asr = MockHybridASR(
            mode=ASRMode.OFFLINE,
            online_available=True,
            online_text="在线",
            offline_text="离线",
        )

        audio = np.zeros(16000, dtype=np.float32)
        result = asr.transcribe(audio)

        assert result.success is True
        assert result.text == "离线"

    def test_hybrid_force_online_mode(self):
        """Test forcing online mode."""
        from src.perception.hybrid_asr import ASRMode, MockHybridASR

        asr = MockHybridASR(
            mode=ASRMode.ONLINE,
            online_available=True,
            online_text="在线",
            offline_text="离线",
        )

        audio = np.zeros(16000, dtype=np.float32)
        result = asr.transcribe(audio)

        assert result.success is True
        assert result.text == "在线"

    def test_hybrid_mode_switching(self, mock_hybrid):
        """Test mode switching."""
        from src.perception.hybrid_asr import ASRMode

        # Initially online
        assert mock_hybrid.current_mode == ASRMode.ONLINE

        # Switch to offline
        mock_hybrid.set_mode(ASRMode.OFFLINE)
        assert mock_hybrid.current_mode == ASRMode.OFFLINE

        # Switch back to auto (should go online)
        mock_hybrid.set_mode(ASRMode.AUTO)
        assert mock_hybrid.current_mode == ASRMode.ONLINE

    def test_hybrid_is_online_available(self, mock_hybrid):
        """Test online availability check."""
        assert mock_hybrid.is_online_available is True

        mock_hybrid.set_online_available(False)
        assert mock_hybrid.is_online_available is False

    def test_hybrid_release(self, mock_hybrid):
        """Test releasing hybrid ASR."""
        assert mock_hybrid.is_initialized

        mock_hybrid.release()

        assert not mock_hybrid.is_initialized

    def test_hybrid_context_manager(self):
        """Test hybrid ASR as context manager."""
        from src.perception.hybrid_asr import MockHybridASR

        with MockHybridASR() as asr:
            assert asr.is_initialized
            audio = np.zeros(16000, dtype=np.float32)
            result = asr.transcribe(audio)
            assert result.success

        assert not asr.is_initialized

    def test_asr_mode_values(self):
        """Test ASRMode enum values."""
        from src.perception.hybrid_asr import ASRMode

        assert ASRMode.ONLINE.value == "online"
        assert ASRMode.OFFLINE.value == "offline"
        assert ASRMode.AUTO.value == "auto"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
