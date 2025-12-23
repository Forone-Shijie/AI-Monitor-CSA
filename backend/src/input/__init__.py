"""
Input Module - Video and Audio Input Sources

This module provides various input sources for the CC-SOP Monitor system:

Video Sources:
    - VideoSource: Abstract base class for all video sources
    - CameraInput: Local camera/webcam input
    - FileInput: Video file input
    - RTSPInput: RTSP/network stream input

Audio Sources:
    - AudioSource: Abstract base class for audio sources
    - MicrophoneInput: Microphone audio capture
    - AudioFileInput: Audio file input

Usage:
    from src.input import FileInput, CameraInput, MicrophoneInput

    # Video from file
    with FileInput("video.mp4") as video:
        for frame in video:
            process(frame.data)

    # Video from camera
    with CameraInput(camera_id=0) as camera:
        for frame in camera:
            process(frame.data)

    # Audio from microphone
    with MicrophoneInput(sample_rate=16000) as mic:
        while True:
            chunk = mic.read_chunk()
            if chunk:
                process(chunk.data)
"""

from .audio_input import (
    AudioChunk,
    AudioFileInput,
    AudioFormat,
    AudioSource,
    AudioSourceInfo,
    MicrophoneInput,
)
from .camera_input import CameraInput
from .file_input import FileInput
from .rtsp_input import RTSPInput
from .video_source import (
    VideoFrame,
    VideoSource,
    VideoSourceInfo,
    VideoSourceType,
)

__all__ = [
    # Video
    "VideoSource",
    "VideoSourceType",
    "VideoFrame",
    "VideoSourceInfo",
    "CameraInput",
    "FileInput",
    "RTSPInput",
    # Audio
    "AudioSource",
    "AudioFormat",
    "AudioChunk",
    "AudioSourceInfo",
    "MicrophoneInput",
    "AudioFileInput",
]
