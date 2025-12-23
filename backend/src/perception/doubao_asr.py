"""
Doubao ASR - Speech recognition using Volcengine (火山引擎) Doubao API.

Provides cloud-based speech recognition with high accuracy for Chinese.
Requires network connectivity and valid API credentials.
"""

import base64
import gzip
import hashlib
import hmac
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import numpy as np

from .asr_engine import (
    ASREngine,
    ASRLanguage,
    ASRResult,
    ASRSegment,
    ASRStatus,
)


@dataclass
class DoubaoConfig:
    """Configuration for Doubao ASR API."""

    app_id: str
    access_token: str
    cluster: str = "volcengine_streaming_common"
    # API endpoints
    api_url: str = "wss://openspeech.bytedance.com/api/v2/asr"
    # Recognition settings
    format: str = "wav"  # Audio format: wav, mp3, pcm
    sample_rate: int = 16000
    bits: int = 16
    channel: int = 1
    language: str = "zh-CN"
    # Timeouts
    connect_timeout: float = 10.0
    read_timeout: float = 30.0


class DoubaoASR(ASREngine):
    """
    ASR engine using Volcengine Doubao API.

    Doubao provides high-accuracy Chinese speech recognition through
    cloud API. Requires valid API credentials.

    Usage:
        config = DoubaoConfig(
            app_id="your_app_id",
            access_token="your_access_token",
        )

        with DoubaoASR(config) as asr:
            result = asr.transcribe(audio_data)
            print(result.text)

    Environment variables:
        DOUBAO_APP_ID: Application ID
        DOUBAO_ACCESS_TOKEN: Access token
        DOUBAO_CLUSTER: Cluster ID (optional)

    Attributes:
        config: DoubaoConfig with API settings
        is_available: Whether API is reachable
    """

    def __init__(
        self,
        config: Optional[DoubaoConfig] = None,
        language: ASRLanguage = ASRLanguage.CHINESE,
    ) -> None:
        """
        Initialize Doubao ASR engine.

        Args:
            config: DoubaoConfig with API credentials
            language: Primary language for recognition
        """
        super().__init__(language=language)

        # Load config from environment if not provided
        if config is None:
            config = self._load_config_from_env()

        self._config = config
        self._is_available = False
        self._last_check_time: float = 0
        self._check_interval = 60.0  # Check availability every 60 seconds

        self._initialize()

    def _load_config_from_env(self) -> DoubaoConfig:
        """Load configuration from environment variables."""
        app_id = os.environ.get("DOUBAO_APP_ID", "")
        access_token = os.environ.get("DOUBAO_ACCESS_TOKEN", "")
        cluster = os.environ.get("DOUBAO_CLUSTER", "volcengine_streaming_common")

        return DoubaoConfig(
            app_id=app_id,
            access_token=access_token,
            cluster=cluster,
        )

    def _initialize(self) -> None:
        """Initialize and check API availability."""
        if not self._config.app_id or not self._config.access_token:
            self._is_initialized = False
            self._status = ASRStatus.ERROR
            return

        # Check if required libraries are available
        try:
            import httpx
            self._httpx = httpx
        except ImportError:
            try:
                import requests
                self._requests = requests
                self._httpx = None
            except ImportError:
                self._is_initialized = False
                self._status = ASRStatus.ERROR
                return

        self._is_initialized = True
        self._status = ASRStatus.IDLE

        # Check availability asynchronously
        self._check_availability()

    def _check_availability(self) -> bool:
        """Check if the API is available."""
        current_time = time.time()

        # Use cached result if within check interval
        if current_time - self._last_check_time < self._check_interval:
            return self._is_available

        self._last_check_time = current_time

        try:
            # Simple connectivity check
            if hasattr(self, '_httpx') and self._httpx:
                response = self._httpx.head(
                    "https://openspeech.bytedance.com",
                    timeout=5.0,
                )
                self._is_available = response.status_code < 500
            elif hasattr(self, '_requests'):
                response = self._requests.head(
                    "https://openspeech.bytedance.com",
                    timeout=5.0,
                )
                self._is_available = response.status_code < 500
            else:
                self._is_available = False
        except Exception:
            self._is_available = False

        return self._is_available

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> ASRResult:
        """
        Transcribe audio data using Doubao API.

        Args:
            audio: Audio data as numpy array (mono, float32)
            sample_rate: Audio sample rate in Hz

        Returns:
            ASRResult containing transcription and metadata
        """
        if not self._is_initialized:
            return ASRResult(
                success=False,
                text="",
                error_message="Doubao ASR not initialized. Check API credentials.",
            )

        if not self._check_availability():
            return ASRResult(
                success=False,
                text="",
                error_message="Doubao API is not available. Check network connection.",
            )

        self._status = ASRStatus.PROCESSING
        start_time = time.time()

        try:
            # Convert audio to WAV bytes
            audio_bytes = self._prepare_audio(audio, sample_rate)

            # Call API
            result = self._call_api(audio_bytes)

            processing_time = time.time() - start_time
            audio_duration = len(audio) / sample_rate

            self._status = ASRStatus.IDLE

            if result.get("success"):
                segments = self._parse_segments(result.get("result", {}))
                text = result.get("result", {}).get("text", "")

                return ASRResult(
                    success=True,
                    text=text,
                    segments=segments,
                    language=self._get_language_code(),
                    confidence=result.get("confidence", 0.9),
                    duration=audio_duration,
                    processing_time=processing_time,
                )
            else:
                return ASRResult(
                    success=False,
                    text="",
                    error_message=result.get("message", "Unknown error"),
                    processing_time=processing_time,
                )

        except Exception as e:
            self._status = ASRStatus.ERROR
            return ASRResult(
                success=False,
                text="",
                error_message=str(e),
                processing_time=time.time() - start_time,
            )

    def transcribe_file(self, file_path: str) -> ASRResult:
        """
        Transcribe audio from file using Doubao API.

        Args:
            file_path: Path to audio file

        Returns:
            ASRResult containing transcription and metadata
        """
        if not os.path.exists(file_path):
            return ASRResult(
                success=False,
                text="",
                error_message=f"File not found: {file_path}",
            )

        if not self._is_initialized:
            return ASRResult(
                success=False,
                text="",
                error_message="Doubao ASR not initialized",
            )

        self._status = ASRStatus.PROCESSING
        start_time = time.time()

        try:
            # Read audio file
            with open(file_path, "rb") as f:
                audio_bytes = f.read()

            # Call API
            result = self._call_api(audio_bytes)

            processing_time = time.time() - start_time

            self._status = ASRStatus.IDLE

            if result.get("success"):
                segments = self._parse_segments(result.get("result", {}))
                text = result.get("result", {}).get("text", "")

                return ASRResult(
                    success=True,
                    text=text,
                    segments=segments,
                    language=self._get_language_code(),
                    confidence=result.get("confidence", 0.9),
                    duration=segments[-1].end_time if segments else 0.0,
                    processing_time=processing_time,
                )
            else:
                return ASRResult(
                    success=False,
                    text="",
                    error_message=result.get("message", "Unknown error"),
                    processing_time=processing_time,
                )

        except Exception as e:
            self._status = ASRStatus.ERROR
            return ASRResult(
                success=False,
                text="",
                error_message=str(e),
                processing_time=time.time() - start_time,
            )

    def _prepare_audio(self, audio: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy audio to WAV bytes."""
        import io
        import wave

        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Convert to int16
        if audio.dtype == np.float32 or audio.dtype == np.float64:
            audio = (audio * 32767).astype(np.int16)
        elif audio.dtype != np.int16:
            audio = audio.astype(np.int16)

        # Resample if needed
        if sample_rate != self._config.sample_rate:
            ratio = self._config.sample_rate / sample_rate
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)

        # Write to WAV bytes
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(self._config.channel)
            wav_file.setsampwidth(self._config.bits // 8)
            wav_file.setframerate(self._config.sample_rate)
            wav_file.writeframes(audio.tobytes())

        return buffer.getvalue()

    def _call_api(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Call Doubao ASR API.

        Uses HTTP REST API for simplicity.
        """
        try:
            # Prepare request
            url = "https://openspeech.bytedance.com/api/v1/asr"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer; {self._config.access_token}",
            }

            # Encode audio as base64
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            payload = {
                "app": {
                    "appid": self._config.app_id,
                    "cluster": self._config.cluster,
                    "token": self._config.access_token,
                },
                "user": {
                    "uid": str(uuid.uuid4()),
                },
                "audio": {
                    "format": self._config.format,
                    "sample_rate": self._config.sample_rate,
                    "bits": self._config.bits,
                    "channel": self._config.channel,
                    "language": self._config.language,
                },
                "request": {
                    "reqid": str(uuid.uuid4()),
                    "sequence": 1,
                },
                "data": audio_base64,
            }

            # Send request
            if hasattr(self, '_httpx') and self._httpx:
                response = self._httpx.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self._config.read_timeout,
                )
                result = response.json()
            elif hasattr(self, '_requests'):
                response = self._requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self._config.read_timeout,
                )
                result = response.json()
            else:
                return {"success": False, "message": "No HTTP client available"}

            # Parse response
            if result.get("code") == 0 or result.get("code") == "0":
                return {
                    "success": True,
                    "result": {
                        "text": result.get("result", ""),
                    },
                    "confidence": 0.9,
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", "API error"),
                }

        except Exception as e:
            return {
                "success": False,
                "message": str(e),
            }

    def _parse_segments(self, result: Dict) -> List[ASRSegment]:
        """Parse segments from API result."""
        segments = []

        # If result contains utterances with timing
        utterances = result.get("utterances", [])
        if utterances:
            for utt in utterances:
                segments.append(
                    ASRSegment(
                        text=utt.get("text", ""),
                        start_time=utt.get("start_time", 0) / 1000.0,
                        end_time=utt.get("end_time", 0) / 1000.0,
                        confidence=utt.get("confidence", 0.9),
                        language=self._get_language_code(),
                    )
                )
        elif result.get("text"):
            # Single segment with full text
            segments.append(
                ASRSegment(
                    text=result.get("text", ""),
                    start_time=0.0,
                    end_time=result.get("duration", 0.0),
                    confidence=0.9,
                    language=self._get_language_code(),
                )
            )

        return segments

    def _get_language_code(self) -> str:
        """Get language code string."""
        if self._language == ASRLanguage.CHINESE:
            return "zh"
        elif self._language == ASRLanguage.ENGLISH:
            return "en"
        return "zh"

    def release(self) -> None:
        """Release resources."""
        self._is_initialized = False
        self._status = ASRStatus.IDLE

    @property
    def is_available(self) -> bool:
        """Check if API is currently available."""
        return self._check_availability()

    @property
    def config(self) -> DoubaoConfig:
        """Get current configuration."""
        return self._config


class MockDoubaoASR(ASREngine):
    """
    Mock Doubao ASR for testing without actual API calls.

    Simulates API behavior for testing purposes.
    """

    def __init__(
        self,
        language: ASRLanguage = ASRLanguage.CHINESE,
        mock_text: str = "豆包语音识别测试结果",
        is_available: bool = True,
    ) -> None:
        """Initialize mock Doubao ASR."""
        super().__init__(language=language)
        self._mock_text = mock_text
        self._mock_available = is_available
        self._is_initialized = True
        self._status = ASRStatus.IDLE

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> ASRResult:
        """Return mock transcription."""
        if not self._mock_available:
            return ASRResult(
                success=False,
                text="",
                error_message="API not available (mock)",
            )

        duration = len(audio) / sample_rate if sample_rate > 0 else 0

        return ASRResult(
            success=True,
            text=self._mock_text,
            segments=[
                ASRSegment(
                    text=self._mock_text,
                    start_time=0.0,
                    end_time=duration,
                    confidence=0.95,
                    language=self._language.value,
                )
            ],
            language=self._language.value,
            confidence=0.95,
            duration=duration,
            processing_time=0.05,
        )

    def transcribe_file(self, file_path: str) -> ASRResult:
        """Return mock transcription for file."""
        if not os.path.exists(file_path):
            return ASRResult(
                success=False,
                text="",
                error_message=f"File not found: {file_path}",
            )

        if not self._mock_available:
            return ASRResult(
                success=False,
                text="",
                error_message="API not available (mock)",
            )

        return ASRResult(
            success=True,
            text=self._mock_text,
            segments=[
                ASRSegment(
                    text=self._mock_text,
                    start_time=0.0,
                    end_time=5.0,
                    confidence=0.95,
                    language=self._language.value,
                )
            ],
            language=self._language.value,
            confidence=0.95,
            duration=5.0,
            processing_time=0.05,
        )

    def release(self) -> None:
        """Release (no-op for mock)."""
        self._is_initialized = False

    @property
    def is_available(self) -> bool:
        """Check mock availability."""
        return self._mock_available

    def set_available(self, available: bool) -> None:
        """Set mock availability for testing."""
        self._mock_available = available
