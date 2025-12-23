"""
Whisper ASR - Local speech recognition using OpenAI Whisper.

Provides offline speech recognition with high accuracy.
Supports multiple model sizes for speed/accuracy tradeoff.
"""

import os
import tempfile
import time
from typing import Optional

import numpy as np

from .asr_engine import (
    ASREngine,
    ASRLanguage,
    ASRResult,
    ASRSegment,
    ASRStatus,
)


class WhisperASR(ASREngine):
    """
    ASR engine using OpenAI Whisper model for local speech recognition.

    Whisper provides high-accuracy speech recognition with word-level
    timestamps. Multiple model sizes are available:

    - tiny: Fastest, lowest accuracy (~1GB VRAM)
    - base: Good balance (~1GB VRAM)
    - small: Better accuracy (~2GB VRAM)
    - medium: High accuracy (~5GB VRAM)
    - large: Best accuracy (~10GB VRAM)

    Usage:
        with WhisperASR(model_size="base") as asr:
            result = asr.transcribe(audio_data, sample_rate=16000)
            print(result.text)

            # Or from file
            result = asr.transcribe_file("audio.wav")
            for segment in result.segments:
                print(f"[{segment.start_time:.2f}s] {segment.text}")

    Attributes:
        model_size: Whisper model size
        device: Compute device (cpu/cuda)
        compute_type: Precision (float32/float16/int8)
    """

    # Available model sizes
    MODEL_SIZES = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]

    def __init__(
        self,
        model_size: str = "base",
        language: ASRLanguage = ASRLanguage.CHINESE,
        device: str = "auto",
        compute_type: str = "auto",
    ) -> None:
        """
        Initialize Whisper ASR engine.

        Args:
            model_size: Model size (tiny/base/small/medium/large)
            language: Primary language for recognition
            device: Device to use (auto/cpu/cuda)
            compute_type: Precision (auto/float32/float16/int8)
        """
        super().__init__(language=language)

        if model_size not in self.MODEL_SIZES:
            raise ValueError(
                f"Invalid model_size: {model_size}. "
                f"Must be one of {self.MODEL_SIZES}"
            )

        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None
        self._whisper = None

        self._initialize()

    def _initialize(self) -> None:
        """Initialize Whisper model."""
        try:
            import whisper

            self._whisper = whisper

            # Determine device
            if self._device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = self._device

            # Load model
            self._model = whisper.load_model(
                self._model_size,
                device=device,
            )

            self._is_initialized = True
            self._status = ASRStatus.IDLE

        except ImportError:
            raise ImportError(
                "openai-whisper is required for WhisperASR. "
                "Install with: pip install openai-whisper"
            )

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
        if not self._is_initialized or self._model is None:
            return ASRResult(
                success=False,
                text="",
                error_message="Whisper model not initialized",
            )

        self._status = ASRStatus.PROCESSING
        start_time = time.time()

        try:
            # Ensure audio is in correct format
            audio = self._prepare_audio(audio, sample_rate)

            # Get language code
            lang = self._get_language_code()

            # Transcribe
            options = {
                "language": lang if lang != "auto" else None,
                "task": "transcribe",
                "verbose": False,
            }

            result = self._model.transcribe(audio, **options)

            # Extract segments
            segments = []
            for seg in result.get("segments", []):
                segments.append(
                    ASRSegment(
                        text=seg["text"].strip(),
                        start_time=seg["start"],
                        end_time=seg["end"],
                        confidence=seg.get("avg_logprob", 0.0),
                        language=result.get("language", lang),
                    )
                )

            # Calculate overall confidence
            if segments:
                avg_confidence = sum(s.confidence for s in segments) / len(segments)
                # Convert log probability to confidence score
                avg_confidence = max(0.0, min(1.0, 1.0 + avg_confidence))
            else:
                avg_confidence = 0.0

            processing_time = time.time() - start_time
            audio_duration = len(audio) / 16000  # Whisper uses 16kHz

            self._status = ASRStatus.IDLE

            return ASRResult(
                success=True,
                text=result["text"].strip(),
                segments=segments,
                language=result.get("language", lang),
                confidence=avg_confidence,
                duration=audio_duration,
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
        Transcribe audio from file.

        Args:
            file_path: Path to audio file

        Returns:
            ASRResult containing transcription and metadata
        """
        if not self._is_initialized or self._model is None:
            return ASRResult(
                success=False,
                text="",
                error_message="Whisper model not initialized",
            )

        if not os.path.exists(file_path):
            return ASRResult(
                success=False,
                text="",
                error_message=f"File not found: {file_path}",
            )

        self._status = ASRStatus.PROCESSING
        start_time = time.time()

        try:
            # Get language code
            lang = self._get_language_code()

            # Transcribe file directly
            options = {
                "language": lang if lang != "auto" else None,
                "task": "transcribe",
                "verbose": False,
            }

            result = self._model.transcribe(file_path, **options)

            # Extract segments
            segments = []
            for seg in result.get("segments", []):
                segments.append(
                    ASRSegment(
                        text=seg["text"].strip(),
                        start_time=seg["start"],
                        end_time=seg["end"],
                        confidence=seg.get("avg_logprob", 0.0),
                        language=result.get("language", lang),
                    )
                )

            # Calculate overall confidence
            if segments:
                avg_confidence = sum(s.confidence for s in segments) / len(segments)
                avg_confidence = max(0.0, min(1.0, 1.0 + avg_confidence))
            else:
                avg_confidence = 0.0

            # Get audio duration from segments
            audio_duration = segments[-1].end_time if segments else 0.0

            processing_time = time.time() - start_time

            self._status = ASRStatus.IDLE

            return ASRResult(
                success=True,
                text=result["text"].strip(),
                segments=segments,
                language=result.get("language", lang),
                confidence=avg_confidence,
                duration=audio_duration,
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

    def _prepare_audio(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Prepare audio for Whisper (16kHz, float32, mono).

        Args:
            audio: Input audio
            sample_rate: Input sample rate

        Returns:
            Prepared audio for Whisper
        """
        # Ensure float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Normalize to -1 to 1 range
        max_val = np.abs(audio).max()
        if max_val > 0:
            audio = audio / max_val

        # Resample to 16kHz if needed
        if sample_rate != 16000:
            try:
                import librosa
                audio = librosa.resample(
                    audio,
                    orig_sr=sample_rate,
                    target_sr=16000,
                )
            except ImportError:
                # Simple resampling without librosa
                ratio = 16000 / sample_rate
                new_length = int(len(audio) * ratio)
                indices = np.linspace(0, len(audio) - 1, new_length)
                audio = np.interp(indices, np.arange(len(audio)), audio)

        return audio.astype(np.float32)

    def _get_language_code(self) -> str:
        """Get Whisper language code from ASRLanguage."""
        if self._language == ASRLanguage.CHINESE:
            return "zh"
        elif self._language == ASRLanguage.ENGLISH:
            return "en"
        else:
            return "auto"

    def release(self) -> None:
        """Release Whisper model resources."""
        if self._model is not None:
            del self._model
            self._model = None

        self._is_initialized = False
        self._status = ASRStatus.IDLE

        # Force garbage collection
        import gc
        gc.collect()

        # Clear CUDA cache if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    @property
    def model_size(self) -> str:
        """Get model size."""
        return self._model_size

    @property
    def device(self) -> str:
        """Get compute device."""
        return self._device


class MockWhisperASR(ASREngine):
    """
    Mock Whisper ASR for testing without actual model.

    Returns predefined responses for testing purposes.
    """

    def __init__(
        self,
        language: ASRLanguage = ASRLanguage.CHINESE,
        mock_text: str = "测试语音识别结果",
    ) -> None:
        """Initialize mock ASR."""
        super().__init__(language=language)
        self._mock_text = mock_text
        self._is_initialized = True
        self._status = ASRStatus.IDLE

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> ASRResult:
        """Return mock transcription."""
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
            processing_time=0.01,
        )

    def transcribe_file(self, file_path: str) -> ASRResult:
        """Return mock transcription for file."""
        if not os.path.exists(file_path):
            return ASRResult(
                success=False,
                text="",
                error_message=f"File not found: {file_path}",
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
            processing_time=0.01,
        )

    def release(self) -> None:
        """Release (no-op for mock)."""
        self._is_initialized = False
