"""
Hybrid ASR - Intelligent ASR with automatic online/offline fallback.

Provides seamless speech recognition that:
1. Uses Doubao API when network is available (faster, more accurate)
2. Falls back to local Whisper when offline (always available)
"""

import time
from enum import Enum
from typing import Optional

import numpy as np

from .asr_engine import (
    ASREngine,
    ASRLanguage,
    ASRResult,
    ASRStatus,
)
from .doubao_asr import DoubaoASR, DoubaoConfig, MockDoubaoASR
from .whisper_asr import MockWhisperASR, WhisperASR


class ASRMode(Enum):
    """Current ASR operation mode."""

    ONLINE = "online"  # Using cloud API
    OFFLINE = "offline"  # Using local model
    AUTO = "auto"  # Automatically switch


class HybridASR(ASREngine):
    """
    Hybrid ASR engine with automatic online/offline switching.

    Prioritizes cloud API (Doubao) for better accuracy and speed,
    automatically falls back to local model (Whisper) when offline.

    Usage:
        # Auto mode - switches automatically
        with HybridASR() as asr:
            result = asr.transcribe(audio_data)
            print(f"Mode: {asr.current_mode}")
            print(f"Text: {result.text}")

        # Force offline mode
        asr = HybridASR(mode=ASRMode.OFFLINE)

        # Custom configuration
        doubao_config = DoubaoConfig(
            app_id="your_app_id",
            access_token="your_token",
        )
        asr = HybridASR(
            doubao_config=doubao_config,
            whisper_model="base",
        )

    Attributes:
        current_mode: Current operation mode (online/offline)
        online_engine: Doubao ASR instance
        offline_engine: Whisper ASR instance
    """

    def __init__(
        self,
        mode: ASRMode = ASRMode.AUTO,
        language: ASRLanguage = ASRLanguage.CHINESE,
        doubao_config: Optional[DoubaoConfig] = None,
        whisper_model: str = "base",
        prefer_online: bool = True,
        fallback_on_error: bool = True,
        check_interval: float = 30.0,
    ) -> None:
        """
        Initialize Hybrid ASR engine.

        Args:
            mode: Operation mode (AUTO/ONLINE/OFFLINE)
            language: Primary language for recognition
            doubao_config: Configuration for Doubao API
            whisper_model: Whisper model size
            prefer_online: Prefer online when both available
            fallback_on_error: Fall back to offline on API errors
            check_interval: Interval for checking online availability
        """
        super().__init__(language=language)

        self._mode = mode
        self._prefer_online = prefer_online
        self._fallback_on_error = fallback_on_error
        self._check_interval = check_interval
        self._last_online_check: float = 0
        self._online_available: bool = False

        # Initialize engines
        self._online_engine: Optional[ASREngine] = None
        self._offline_engine: Optional[ASREngine] = None
        self._current_mode: ASRMode = ASRMode.OFFLINE

        self._doubao_config = doubao_config
        self._whisper_model = whisper_model

        self._initialize()

    def _initialize(self) -> None:
        """Initialize online and offline engines."""
        # Initialize online engine (Doubao)
        try:
            self._online_engine = DoubaoASR(
                config=self._doubao_config,
                language=self._language,
            )
        except Exception:
            self._online_engine = None

        # Initialize offline engine (Whisper) - lazy load
        # Only initialize when needed to save resources
        self._offline_engine = None
        self._offline_initialized = False

        # Determine initial mode
        self._update_mode()

        self._is_initialized = True
        self._status = ASRStatus.IDLE

    def _ensure_offline_engine(self) -> bool:
        """Ensure offline engine is initialized."""
        if self._offline_engine is not None:
            return True

        if self._offline_initialized:
            return False  # Already tried, failed

        try:
            self._offline_engine = WhisperASR(
                model_size=self._whisper_model,
                language=self._language,
            )
            self._offline_initialized = True
            return True
        except ImportError:
            # Whisper not available, use mock for graceful degradation
            self._offline_engine = MockWhisperASR(
                language=self._language,
                mock_text="[本地语音识别不可用]",
            )
            self._offline_initialized = True
            return True
        except Exception:
            self._offline_initialized = True
            return False

    def _check_online_available(self) -> bool:
        """Check if online API is available."""
        current_time = time.time()

        # Use cached result if within check interval
        if current_time - self._last_online_check < self._check_interval:
            return self._online_available

        self._last_online_check = current_time

        if self._online_engine is None:
            self._online_available = False
            return False

        # Check if Doubao is available
        if hasattr(self._online_engine, 'is_available'):
            self._online_available = self._online_engine.is_available
        else:
            self._online_available = self._online_engine.is_initialized

        return self._online_available

    def _update_mode(self) -> None:
        """Update current mode based on availability."""
        if self._mode == ASRMode.ONLINE:
            self._current_mode = ASRMode.ONLINE
        elif self._mode == ASRMode.OFFLINE:
            self._current_mode = ASRMode.OFFLINE
        else:  # AUTO
            if self._prefer_online and self._check_online_available():
                self._current_mode = ASRMode.ONLINE
            else:
                self._current_mode = ASRMode.OFFLINE

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> ASRResult:
        """
        Transcribe audio using best available engine.

        Args:
            audio: Audio data as numpy array (mono, float32)
            sample_rate: Audio sample rate in Hz

        Returns:
            ASRResult containing transcription and metadata
        """
        self._update_mode()
        self._status = ASRStatus.PROCESSING

        result: Optional[ASRResult] = None

        # Try online first if preferred
        if self._current_mode == ASRMode.ONLINE and self._online_engine:
            result = self._online_engine.transcribe(audio, sample_rate)

            if result.success:
                self._status = ASRStatus.IDLE
                return self._add_mode_info(result, ASRMode.ONLINE)

            # Fall back to offline if enabled
            if self._fallback_on_error:
                self._current_mode = ASRMode.OFFLINE

        # Use offline engine
        if self._current_mode == ASRMode.OFFLINE:
            if self._ensure_offline_engine() and self._offline_engine:
                result = self._offline_engine.transcribe(audio, sample_rate)

                if result.success:
                    self._status = ASRStatus.IDLE
                    return self._add_mode_info(result, ASRMode.OFFLINE)

        # Both failed
        self._status = ASRStatus.ERROR
        return ASRResult(
            success=False,
            text="",
            error_message="所有语音识别引擎都不可用",
        )

    def transcribe_file(self, file_path: str) -> ASRResult:
        """
        Transcribe audio file using best available engine.

        Args:
            file_path: Path to audio file

        Returns:
            ASRResult containing transcription and metadata
        """
        self._update_mode()
        self._status = ASRStatus.PROCESSING

        result: Optional[ASRResult] = None

        # Try online first if preferred
        if self._current_mode == ASRMode.ONLINE and self._online_engine:
            result = self._online_engine.transcribe_file(file_path)

            if result.success:
                self._status = ASRStatus.IDLE
                return self._add_mode_info(result, ASRMode.ONLINE)

            # Fall back to offline if enabled
            if self._fallback_on_error:
                self._current_mode = ASRMode.OFFLINE

        # Use offline engine
        if self._current_mode == ASRMode.OFFLINE:
            if self._ensure_offline_engine() and self._offline_engine:
                result = self._offline_engine.transcribe_file(file_path)

                if result.success:
                    self._status = ASRStatus.IDLE
                    return self._add_mode_info(result, ASRMode.OFFLINE)

        # Both failed
        self._status = ASRStatus.ERROR
        return ASRResult(
            success=False,
            text="",
            error_message="所有语音识别引擎都不可用",
        )

    def _add_mode_info(self, result: ASRResult, mode: ASRMode) -> ASRResult:
        """Add mode information to result."""
        # We can add mode info in error_message field when there's no error
        # or we could extend ASRResult in the future
        return result

    def release(self) -> None:
        """Release all engine resources."""
        if self._online_engine:
            self._online_engine.release()
            self._online_engine = None

        if self._offline_engine:
            self._offline_engine.release()
            self._offline_engine = None

        self._is_initialized = False
        self._status = ASRStatus.IDLE

    def set_mode(self, mode: ASRMode) -> None:
        """
        Set operation mode.

        Args:
            mode: New operation mode
        """
        self._mode = mode
        self._update_mode()

    def force_online_check(self) -> bool:
        """Force an immediate online availability check."""
        self._last_online_check = 0
        return self._check_online_available()

    @property
    def current_mode(self) -> ASRMode:
        """Get current operation mode."""
        return self._current_mode

    @property
    def is_online_available(self) -> bool:
        """Check if online API is available."""
        return self._check_online_available()

    @property
    def online_engine(self) -> Optional[ASREngine]:
        """Get online engine instance."""
        return self._online_engine

    @property
    def offline_engine(self) -> Optional[ASREngine]:
        """Get offline engine instance."""
        return self._offline_engine


class MockHybridASR(HybridASR):
    """
    Mock Hybrid ASR for testing.

    Simulates online/offline switching behavior.
    """

    def __init__(
        self,
        mode: ASRMode = ASRMode.AUTO,
        language: ASRLanguage = ASRLanguage.CHINESE,
        online_available: bool = True,
        online_text: str = "在线识别结果",
        offline_text: str = "离线识别结果",
    ) -> None:
        """Initialize mock hybrid ASR."""
        # Don't call parent __init__, set up mocks directly
        ASREngine.__init__(self, language=language)

        self._mode = mode
        self._prefer_online = True
        self._fallback_on_error = True
        self._check_interval = 30.0
        self._last_online_check = 0
        self._online_available = online_available

        # Create mock engines
        self._online_engine = MockDoubaoASR(
            language=language,
            mock_text=online_text,
            is_available=online_available,
        )
        self._offline_engine = MockWhisperASR(
            language=language,
            mock_text=offline_text,
        )
        self._offline_initialized = True

        # Set initial mode
        if mode == ASRMode.ONLINE:
            self._current_mode = ASRMode.ONLINE
        elif mode == ASRMode.OFFLINE:
            self._current_mode = ASRMode.OFFLINE
        else:
            self._current_mode = ASRMode.ONLINE if online_available else ASRMode.OFFLINE

        self._is_initialized = True
        self._status = ASRStatus.IDLE

    def set_online_available(self, available: bool) -> None:
        """Set online availability for testing."""
        self._online_available = available
        if hasattr(self._online_engine, 'set_available'):
            self._online_engine.set_available(available)
        self._update_mode()

    def _check_online_available(self) -> bool:
        """Check mock online availability."""
        return self._online_available

    def _ensure_offline_engine(self) -> bool:
        """Offline engine is always ready in mock."""
        return True
