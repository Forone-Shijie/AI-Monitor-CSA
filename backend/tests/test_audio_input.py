"""
Unit tests for audio input sources.

Tests MicrophoneInput, AudioFileInput and related classes.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.input.audio_input import (
    AudioChunk,
    AudioFileInput,
    AudioFormat,
    AudioSourceInfo,
    MicrophoneInput,
)


class TestAudioChunk:
    """Tests for AudioChunk dataclass."""

    def test_audio_chunk_creation(self):
        """Test creating an AudioChunk."""
        data = np.zeros((8000,), dtype=np.float32)
        chunk = AudioChunk(
            data=data,
            timestamp=1.5,
            sample_rate=16000,
            channels=1,
            duration=0.5,
        )

        assert chunk.sample_rate == 16000
        assert chunk.channels == 1
        assert chunk.timestamp == 1.5
        assert chunk.duration == 0.5
        assert len(chunk.data) == 8000


class TestAudioSourceInfo:
    """Tests for AudioSourceInfo dataclass."""

    def test_audio_source_info(self):
        """Test AudioSourceInfo creation."""
        info = AudioSourceInfo(
            device_id=0,
            device_name="Test Microphone",
            sample_rate=16000,
            channels=1,
            format=AudioFormat.FLOAT32,
            chunk_size=8000,
        )

        assert info.device_id == 0
        assert info.device_name == "Test Microphone"
        assert info.sample_rate == 16000
        assert info.channels == 1
        assert info.format == AudioFormat.FLOAT32


class TestAudioFormat:
    """Tests for AudioFormat enum."""

    def test_audio_formats(self):
        """Test audio format values."""
        assert AudioFormat.INT16.value == "int16"
        assert AudioFormat.INT32.value == "int32"
        assert AudioFormat.FLOAT32.value == "float32"


class TestMicrophoneInput:
    """Tests for MicrophoneInput class."""

    @pytest.fixture
    def mock_sounddevice(self):
        """Create mock sounddevice module."""
        with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
            import sys

            sd = sys.modules["sounddevice"]

            # Mock query_devices
            sd.query_devices.return_value = {
                "name": "Test Microphone",
                "max_input_channels": 2,
                "default_samplerate": 44100,
            }

            # Mock InputStream
            mock_stream = MagicMock()
            sd.InputStream.return_value = mock_stream

            yield sd, mock_stream

    def test_microphone_init(self, mock_sounddevice):
        """Test MicrophoneInput initialization."""
        sd, mock_stream = mock_sounddevice

        mic = MicrophoneInput(sample_rate=16000, channels=1)

        assert mic._sample_rate == 16000
        assert mic._channels == 1
        assert not mic.is_recording

    def test_microphone_info(self, mock_sounddevice):
        """Test getting microphone info."""
        sd, mock_stream = mock_sounddevice

        mic = MicrophoneInput(sample_rate=16000)

        info = mic.get_info()

        assert info.sample_rate == 16000
        assert info.channels == 1
        assert info.format == AudioFormat.FLOAT32

    def test_microphone_context_manager(self, mock_sounddevice):
        """Test MicrophoneInput as context manager."""
        sd, mock_stream = mock_sounddevice

        with MicrophoneInput(sample_rate=16000) as mic:
            assert mic.is_recording
            mock_stream.start.assert_called_once()

        mock_stream.stop.assert_called_once()


class TestAudioFileInput:
    """Tests for AudioFileInput class."""

    @pytest.fixture
    def mock_soundfile(self):
        """Create mock soundfile module."""
        with patch.dict("sys.modules", {"soundfile": MagicMock()}):
            import sys

            sf = sys.modules["soundfile"]

            # Create mock audio data (2 seconds of mono audio at 16kHz)
            mock_data = np.zeros((32000, 1), dtype=np.float32)
            sf.read.return_value = (mock_data, 16000)

            yield sf

    def test_audio_file_not_found(self):
        """Test AudioFileInput raises error for non-existent file."""
        with pytest.raises(FileNotFoundError):
            AudioFileInput("/nonexistent/path/audio.wav")

    def test_audio_file_read(self, mock_soundfile, tmp_path):
        """Test reading audio from file."""
        # Create temporary file
        test_file = tmp_path / "test.wav"
        test_file.touch()

        audio = AudioFileInput(str(test_file), chunk_duration=0.5)

        audio.start()

        # Read first chunk
        chunk = audio.read_chunk()

        assert chunk is not None
        assert chunk.sample_rate == 16000
        assert chunk.duration <= 0.5

        audio.stop()

    def test_audio_file_duration(self, mock_soundfile, tmp_path):
        """Test getting audio file duration."""
        test_file = tmp_path / "test.wav"
        test_file.touch()

        audio = AudioFileInput(str(test_file))

        # 32000 samples at 16000 Hz = 2 seconds
        assert audio.get_duration() == 2.0

    def test_audio_file_seek(self, mock_soundfile, tmp_path):
        """Test seeking in audio file."""
        test_file = tmp_path / "test.wav"
        test_file.touch()

        audio = AudioFileInput(str(test_file))

        audio.seek(1.0)
        assert audio.get_position() == 1.0

    def test_audio_file_info(self, mock_soundfile, tmp_path):
        """Test audio file info."""
        test_file = tmp_path / "test.wav"
        test_file.touch()

        audio = AudioFileInput(str(test_file))

        info = audio.get_info()

        assert info.sample_rate == 16000
        assert info.channels == 1
        assert info.device_id is None

    def test_audio_file_context_manager(self, mock_soundfile, tmp_path):
        """Test AudioFileInput as context manager."""
        test_file = tmp_path / "test.wav"
        test_file.touch()

        with AudioFileInput(str(test_file)) as audio:
            assert audio.is_recording

        assert not audio.is_recording


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
