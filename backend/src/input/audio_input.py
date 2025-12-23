"""
Audio Input - Audio capture implementation.

Captures audio from microphone or audio devices for ASR processing.
"""

import queue
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np


class AudioFormat(Enum):
    """Audio sample format."""

    INT16 = "int16"
    INT32 = "int32"
    FLOAT32 = "float32"


@dataclass
class AudioChunk:
    """Audio data chunk container."""

    data: np.ndarray  # Audio samples
    timestamp: float  # Chunk start timestamp
    sample_rate: int  # Sample rate in Hz
    channels: int  # Number of channels
    duration: float  # Chunk duration in seconds


@dataclass
class AudioSourceInfo:
    """Audio source information."""

    device_id: Optional[int]
    device_name: str
    sample_rate: int
    channels: int
    format: AudioFormat
    chunk_size: int


class AudioSource(ABC):
    """
    Abstract base class for audio sources.

    All audio input implementations must inherit from this class.
    """

    def __init__(self) -> None:
        self._is_recording: bool = False
        self._total_samples: int = 0

    @abstractmethod
    def start(self) -> None:
        """Start audio capture."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture."""
        pass

    @abstractmethod
    def read_chunk(self, timeout: float = 1.0) -> Optional[AudioChunk]:
        """
        Read an audio chunk.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            AudioChunk or None if timeout
        """
        pass

    @abstractmethod
    def get_info(self) -> AudioSourceInfo:
        """Get audio source information."""
        pass

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def __enter__(self) -> "AudioSource":
        """Context manager entry - start recording."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Context manager exit - stop recording."""
        self.stop()


class MicrophoneInput(AudioSource):
    """
    Microphone audio input using sounddevice.

    Captures audio from the system microphone.

    Usage:
        with MicrophoneInput(sample_rate=16000) as mic:
            while True:
                chunk = mic.read_chunk()
                if chunk:
                    # Process chunk.data
                    pass
    """

    def __init__(
        self,
        device_id: Optional[int] = None,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration: float = 0.5,
        buffer_chunks: int = 10,
        format: AudioFormat = AudioFormat.FLOAT32,
    ) -> None:
        """
        Initialize microphone input.

        Args:
            device_id: Audio device ID (None for default)
            sample_rate: Sample rate in Hz (16000 recommended for ASR)
            channels: Number of channels (1 for mono)
            chunk_duration: Duration of each chunk in seconds
            buffer_chunks: Number of chunks to buffer
            format: Audio sample format
        """
        super().__init__()

        self._device_id = device_id
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_duration = chunk_duration
        self._format = format

        # Calculate chunk size in samples
        self._chunk_size = int(sample_rate * chunk_duration)

        # Audio buffer queue
        self._audio_queue: queue.Queue[AudioChunk] = queue.Queue(maxsize=buffer_chunks)

        # Sounddevice stream (lazy initialization)
        self._stream = None
        self._start_time: float = 0.0

        # Get device name
        self._device_name = self._get_device_name()

    def _get_device_name(self) -> str:
        """Get the name of the audio device."""
        try:
            import sounddevice as sd

            if self._device_id is None:
                return sd.query_devices(kind="input")["name"]
            return sd.query_devices(self._device_id)["name"]
        except Exception:
            return "Unknown Device"

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info: dict, status: int
    ) -> None:
        """
        Callback function for audio stream.

        Called by sounddevice when audio data is available.
        """
        if status:
            pass  # Handle status flags if needed

        timestamp = time.time() - self._start_time
        duration = frames / self._sample_rate

        chunk = AudioChunk(
            data=indata.copy(),
            timestamp=timestamp,
            sample_rate=self._sample_rate,
            channels=self._channels,
            duration=duration,
        )

        try:
            self._audio_queue.put_nowait(chunk)
        except queue.Full:
            # Drop oldest chunk if buffer is full
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(chunk)
            except queue.Empty:
                pass

        self._total_samples += frames

    def start(self) -> None:
        """Start audio capture."""
        if self._is_recording:
            return

        try:
            import sounddevice as sd

            # Determine dtype based on format
            dtype_map = {
                AudioFormat.INT16: "int16",
                AudioFormat.INT32: "int32",
                AudioFormat.FLOAT32: "float32",
            }

            self._stream = sd.InputStream(
                device=self._device_id,
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=dtype_map[self._format],
                blocksize=self._chunk_size,
                callback=self._audio_callback,
            )

            self._start_time = time.time()
            self._stream.start()
            self._is_recording = True

        except ImportError:
            raise ImportError(
                "sounddevice is required for microphone input. "
                "Install with: pip install sounddevice"
            )

    def stop(self) -> None:
        """Stop audio capture."""
        if not self._is_recording:
            return

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_recording = False

    def read_chunk(self, timeout: float = 1.0) -> Optional[AudioChunk]:
        """
        Read an audio chunk from the buffer.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            AudioChunk or None if timeout
        """
        if not self._is_recording:
            return None

        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_info(self) -> AudioSourceInfo:
        """Get audio source information."""
        return AudioSourceInfo(
            device_id=self._device_id,
            device_name=self._device_name,
            sample_rate=self._sample_rate,
            channels=self._channels,
            format=self._format,
            chunk_size=self._chunk_size,
        )

    def get_buffer_size(self) -> int:
        """Get current buffer queue size."""
        return self._audio_queue.qsize()

    def clear_buffer(self) -> None:
        """Clear the audio buffer."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    @staticmethod
    def list_devices() -> list[dict]:
        """
        List available audio input devices.

        Returns:
            List of device info dictionaries
        """
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            input_devices = []

            for i, device in enumerate(devices):
                if device["max_input_channels"] > 0:
                    input_devices.append(
                        {
                            "id": i,
                            "name": device["name"],
                            "channels": device["max_input_channels"],
                            "sample_rate": device["default_samplerate"],
                        }
                    )

            return input_devices

        except ImportError:
            return []


class AudioFileInput(AudioSource):
    """
    Audio file input.

    Reads audio from WAV or other audio files.

    Usage:
        with AudioFileInput("audio.wav") as audio:
            while True:
                chunk = audio.read_chunk()
                if chunk is None:
                    break
                # Process chunk.data
    """

    def __init__(
        self,
        file_path: str,
        chunk_duration: float = 0.5,
    ) -> None:
        """
        Initialize audio file input.

        Args:
            file_path: Path to audio file
            chunk_duration: Duration of each chunk in seconds
        """
        super().__init__()

        self._file_path = Path(file_path)
        self._chunk_duration = chunk_duration

        if not self._file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Load audio file
        try:
            import soundfile as sf

            self._data, self._sample_rate = sf.read(str(self._file_path))

            # Ensure 2D array (samples x channels)
            if len(self._data.shape) == 1:
                self._data = self._data.reshape(-1, 1)

            self._channels = self._data.shape[1]
            self._total_frames = self._data.shape[0]
            self._chunk_size = int(self._sample_rate * chunk_duration)
            self._current_position = 0

        except ImportError:
            raise ImportError(
                "soundfile is required for audio file input. "
                "Install with: pip install soundfile"
            )

    def start(self) -> None:
        """Start reading (reset position)."""
        self._current_position = 0
        self._is_recording = True

    def stop(self) -> None:
        """Stop reading."""
        self._is_recording = False

    def read_chunk(self, timeout: float = 1.0) -> Optional[AudioChunk]:
        """
        Read an audio chunk from the file.

        Args:
            timeout: Not used for file input

        Returns:
            AudioChunk or None if end of file
        """
        if not self._is_recording:
            return None

        if self._current_position >= self._total_frames:
            return None

        # Calculate chunk boundaries
        end_position = min(
            self._current_position + self._chunk_size, self._total_frames
        )
        chunk_data = self._data[self._current_position : end_position]

        timestamp = self._current_position / self._sample_rate
        duration = (end_position - self._current_position) / self._sample_rate

        chunk = AudioChunk(
            data=chunk_data,
            timestamp=timestamp,
            sample_rate=self._sample_rate,
            channels=self._channels,
            duration=duration,
        )

        self._current_position = end_position
        return chunk

    def get_info(self) -> AudioSourceInfo:
        """Get audio source information."""
        return AudioSourceInfo(
            device_id=None,
            device_name=str(self._file_path),
            sample_rate=self._sample_rate,
            channels=self._channels,
            format=AudioFormat.FLOAT32,
            chunk_size=self._chunk_size,
        )

    def seek(self, position: float) -> None:
        """
        Seek to a position in the audio file.

        Args:
            position: Position in seconds
        """
        self._current_position = int(position * self._sample_rate)
        self._current_position = max(
            0, min(self._current_position, self._total_frames)
        )

    def get_duration(self) -> float:
        """Get total audio duration in seconds."""
        return self._total_frames / self._sample_rate

    def get_position(self) -> float:
        """Get current position in seconds."""
        return self._current_position / self._sample_rate
