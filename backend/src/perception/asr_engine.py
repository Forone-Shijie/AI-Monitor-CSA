"""
ASR Engine - Abstract base class for Automatic Speech Recognition.

Defines the interface for all ASR implementations (e.g., FunASR Paraformer).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np


class ASRStatus(Enum):
    """ASR engine status."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


class ASRLanguage(Enum):
    """Supported languages for ASR."""

    CHINESE = "zh"
    ENGLISH = "en"
    AUTO = "auto"


@dataclass
class ASRSegment:
    """A single transcribed segment with timing information."""

    text: str  # Transcribed text
    start_time: float  # Start time in seconds
    end_time: float  # End time in seconds
    confidence: float  # Confidence score (0-1)
    language: str = "zh"  # Detected/specified language

    @property
    def duration(self) -> float:
        """Get segment duration."""
        return self.end_time - self.start_time

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "confidence": self.confidence,
            "language": self.language,
            "duration": self.duration,
        }


@dataclass
class ASRResult:
    """Result of speech recognition on audio input."""

    # Recognition status
    success: bool  # Whether recognition succeeded

    # Full transcription
    text: str  # Complete transcribed text

    # Segments with timing
    segments: List[ASRSegment] = field(default_factory=list)

    # Metadata
    language: str = "zh"  # Primary language
    confidence: float = 0.0  # Overall confidence
    duration: float = 0.0  # Total audio duration in seconds
    processing_time: float = 0.0  # Time taken for processing

    # Error information
    error_message: Optional[str] = None

    def get_text_at_time(self, timestamp: float) -> Optional[ASRSegment]:
        """Get segment containing the given timestamp."""
        for segment in self.segments:
            if segment.start_time <= timestamp <= segment.end_time:
                return segment
        return None

    def get_segments_in_range(
        self, start: float, end: float
    ) -> List[ASRSegment]:
        """Get all segments within a time range."""
        return [
            seg for seg in self.segments
            if seg.start_time < end and seg.end_time > start
        ]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "text": self.text,
            "segments": [seg.to_dict() for seg in self.segments],
            "language": self.language,
            "confidence": self.confidence,
            "duration": self.duration,
            "processing_time": self.processing_time,
            "error_message": self.error_message,
        }


class ASREngine(ABC):
    """
    Abstract base class for ASR (Automatic Speech Recognition) engines.

    All ASR implementations must inherit from this class.

    Usage:
        # Example with FunASR (to be implemented)
        # engine = FunASREngine()
        # result = engine.transcribe(audio_data, sample_rate=16000)
        # if result.success:
        #     print(f"Transcription: {result.text}")
        #     for segment in result.segments:
        #         print(f"  [{segment.start_time:.2f}s] {segment.text}")
    """

    def __init__(
        self,
        language: ASRLanguage = ASRLanguage.CHINESE,
    ) -> None:
        """
        Initialize ASR engine.

        Args:
            language: Primary language for recognition
        """
        self._language = language
        self._is_initialized: bool = False
        self._status: ASRStatus = ASRStatus.IDLE

    @abstractmethod
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> ASRResult:
        """
        Transcribe audio data to text.

        Args:
            audio: Audio data as numpy array (mono, float32)
            sample_rate: Audio sample rate in Hz

        Returns:
            ASRResult containing transcription and metadata
        """
        pass

    @abstractmethod
    def transcribe_file(self, file_path: str) -> ASRResult:
        """
        Transcribe audio from file.

        Args:
            file_path: Path to audio file

        Returns:
            ASRResult containing transcription and metadata
        """
        pass

    @abstractmethod
    def release(self) -> None:
        """Release engine resources."""
        pass

    @property
    def is_initialized(self) -> bool:
        """Check if engine is initialized."""
        return self._is_initialized

    @property
    def status(self) -> ASRStatus:
        """Get current engine status."""
        return self._status

    @property
    def language(self) -> ASRLanguage:
        """Get configured language."""
        return self._language

    def __enter__(self) -> "ASREngine":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Context manager exit - release resources."""
        self.release()


# Standard terminology for cabin crew communications
STANDARD_TERMINOLOGY = {
    # Emergency commands
    "brace": ["brace", "防冲击", "防冲击姿势"],
    "evacuate": ["evacuate", "撤离", "紧急撤离", "疏散"],
    "fire": ["fire", "火情", "火警", "着火"],

    # Safety checks
    "check_seatbelt": ["系好安全带", "请系好安全带", "fasten seatbelt"],
    "check_tray": ["收起小桌板", "请收起小桌板", "tray table up"],
    "check_seat": ["调直座椅靠背", "请调直座椅靠背", "seat upright"],

    # Communication
    "confirm": ["确认", "收到", "明白", "roger", "confirm", "copy"],
    "report": ["报告", "汇报", "report"],
    "standby": ["待命", "等待", "standby"],

    # Crew coordination
    "ready": ["准备完毕", "ready", "prepared"],
    "clear": ["已清空", "安全", "clear"],
    "assist": ["协助", "帮助", "assist"],
}
