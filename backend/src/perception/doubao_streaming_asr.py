"""
Doubao Streaming ASR - Real-time speech recognition using Volcengine WebSocket API.

火山引擎流式语音识别 API (v3)
Documentation: https://www.volcengine.com/docs/6561/1354869

Uses WebSocket binary protocol for real-time audio streaming and recognition.
"""

import asyncio
import gzip
import json
import logging
import os
import struct
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    WebSocketClientProtocol = Any

logger = logging.getLogger(__name__)


# Protocol constants
PROTOCOL_VERSION = 0b0001
HEADER_SIZE = 0b0001

# Message types
FULL_CLIENT_REQUEST = 0b0001      # First request with config
AUDIO_ONLY_REQUEST = 0b0010       # Audio data only
FULL_SERVER_RESPONSE = 0b1001     # Server response with result
SERVER_ACK = 0b1011               # Server acknowledgement
SERVER_ERROR = 0b1111             # Server error

# Message type specific flags
NO_SEQUENCE = 0b0000
SEQUENCE_POSITIVE = 0b0001        # sequence > 0
SEQUENCE_LAST = 0b0010            # last message (sequence < 0)
SEQUENCE_NEGATIVE = 0b0011        # sequence < 0

# Serialization methods
NO_SERIALIZATION = 0b0000
JSON_SERIALIZATION = 0b0001
CUSTOM_SERIALIZATION = 0b1111

# Compression methods
NO_COMPRESSION = 0b0000
GZIP_COMPRESSION = 0b0001
CUSTOM_COMPRESSION = 0b1111


@dataclass
class DoubaoStreamingConfig:
    """Configuration for Doubao Streaming ASR."""

    app_id: str
    access_key: str
    resource_id: str = "volc.bigasr.sauc.duration"
    cluster: str = "volcengine_streaming_common"

    # WebSocket endpoint
    ws_url: str = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"

    # Audio settings
    format: str = "pcm"
    sample_rate: int = 16000
    bits: int = 16
    channel: int = 1
    language: str = "zh-CN"

    # Connection settings
    connect_timeout: float = 10.0
    receive_timeout: float = 30.0


@dataclass
class ASRStreamResult:
    """Result from streaming ASR."""

    text: str
    is_final: bool
    confidence: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    sequence: int = 0


class DoubaoStreamingASR:
    """
    Real-time streaming ASR using Volcengine WebSocket API.

    Usage:
        async with DoubaoStreamingASR(config) as asr:
            await asr.send_audio(audio_chunk)
            result = await asr.receive_result()
            print(result.text)

    Environment variables:
        DOUBAO_APP_ID: Application ID
        DOUBAO_ACCESS_TOKEN: Access token (used as access_key)
    """

    def __init__(self, config: Optional[DoubaoStreamingConfig] = None):
        """Initialize streaming ASR."""
        if not HAS_WEBSOCKETS:
            raise ImportError("websockets library required: pip install websockets")

        if config is None:
            config = self._load_config_from_env()

        self._config = config
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._sequence = 0
        self._connect_id = ""

    def _load_config_from_env(self) -> DoubaoStreamingConfig:
        """Load configuration from environment variables."""
        return DoubaoStreamingConfig(
            app_id=os.environ.get("DOUBAO_APP_ID", ""),
            access_key=os.environ.get("DOUBAO_ACCESS_TOKEN", ""),
            cluster=os.environ.get("DOUBAO_CLUSTER", "volcengine_streaming_common"),
        )

    async def connect(self) -> bool:
        """
        Establish WebSocket connection.

        Returns:
            True if connection successful
        """
        if self._connected:
            return True

        if not self._config.app_id or not self._config.access_key:
            logger.error("Missing DOUBAO_APP_ID or DOUBAO_ACCESS_TOKEN")
            return False

        self._connect_id = str(uuid.uuid4())

        headers = {
            "X-Api-App-Key": self._config.app_id,
            "X-Api-Access-Key": self._config.access_key,
            "X-Api-Resource-Id": self._config.resource_id,
            "X-Api-Connect-Id": self._connect_id,
        }

        try:
            self._ws = await asyncio.wait_for(
                websockets.connect(
                    self._config.ws_url,
                    additional_headers=headers,
                ),
                timeout=self._config.connect_timeout,
            )
            self._connected = True
            self._sequence = 0
            logger.info(f"Connected to Doubao ASR: {self._connect_id}")

            # Send initial config
            await self._send_config()

            # Wait for server ACK before proceeding
            ack_received = await self._wait_for_ack(timeout=5.0)
            if not ack_received:
                logger.error("Failed to receive config ACK from server")
                self._connected = False
                await self._ws.close()
                self._ws = None
                return False

            return True

        except asyncio.TimeoutError:
            logger.error("Connection timeout")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._ws:
            try:
                # Send last packet to signal end
                await self._send_last_audio()
                await self._ws.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._ws = None
                self._connected = False
                logger.info("Disconnected from Doubao ASR")

    async def __aenter__(self) -> "DoubaoStreamingASR":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    def _build_header(
        self,
        msg_type: int,
        msg_type_flags: int = SEQUENCE_POSITIVE,
        serial_method: int = NO_SERIALIZATION,
        compress_method: int = GZIP_COMPRESSION,
    ) -> bytes:
        """
        Build 4-byte protocol header.

        Header format (32 bits):
        - bits 28-31: protocol version (4 bits)
        - bits 24-27: header size (4 bits, value * 4 = actual size)
        - bits 20-23: message type (4 bits)
        - bits 16-19: message type specific flags (4 bits)
        - bits 12-15: serialization method (4 bits)
        - bits 8-11: compression method (4 bits)
        - bits 0-7: reserved (8 bits)
        """
        header = 0
        header |= (PROTOCOL_VERSION & 0x0F) << 28
        header |= (HEADER_SIZE & 0x0F) << 24
        header |= (msg_type & 0x0F) << 20
        header |= (msg_type_flags & 0x0F) << 16
        header |= (serial_method & 0x0F) << 12
        header |= (compress_method & 0x0F) << 8
        # Reserved bits 0-7 are 0

        return struct.pack(">I", header)

    async def _send_config(self) -> None:
        """Send initial configuration request."""
        if not self._ws:
            return

        # Build config payload (火山引擎 API v3 格式)
        # 注意：认证信息通过 HTTP headers 传递，payload 不需要 app 字段
        config_payload = {
            "user": {
                "uid": self._connect_id,
            },
            "audio": {
                "format": self._config.format,
                "rate": self._config.sample_rate,
                "bits": self._config.bits,
                "channel": self._config.channel,
                "language": self._config.language,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "model_name": "bigmodel",
                "enable_punc": True,
                "enable_itn": True,
                "enable_ddc": False,
                "show_utterances": True,
                "result_type": "single",      # 返回中间结果，降低延迟
                "vad_silence_time": 500,      # 尾部静音 500ms 即判定句尾
            },
        }

        # Compress payload
        payload_json = json.dumps(config_payload).encode("utf-8")
        payload_compressed = gzip.compress(payload_json)

        # Build message: [Header 4B] [Sequence 4B] [Payload_Size 4B] [Payload]
        header = self._build_header(
            msg_type=FULL_CLIENT_REQUEST,
            msg_type_flags=SEQUENCE_POSITIVE,
            serial_method=JSON_SERIALIZATION,
            compress_method=GZIP_COMPRESSION,
        )
        self._sequence = 1
        sequence = struct.pack(">i", self._sequence)  # 有符号整数
        payload_size = struct.pack(">I", len(payload_compressed))

        message = header + sequence + payload_size + payload_compressed
        await self._ws.send(message)

        logger.debug("Sent initial config")

    async def _wait_for_ack(self, timeout: float = 5.0) -> bool:
        """
        Wait for server acknowledgement after sending config.

        Args:
            timeout: Maximum time to wait for ACK in seconds

        Returns:
            True if ACK received successfully, False on error
        """
        if not self._ws:
            return False

        try:
            data = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
            result = self._parse_response(data)

            # _parse_response sets _connected = False on SERVER_ERROR
            if not self._connected:
                return False

            logger.debug("Received config ACK from server")
            return True

        except asyncio.TimeoutError:
            logger.error("Timeout waiting for server ACK")
            return False
        except Exception as e:
            logger.error(f"Failed to receive ACK: {e}")
            return False

    async def send_audio(self, audio_data: bytes) -> bool:
        """
        Send audio data chunk.

        Args:
            audio_data: PCM audio bytes (16-bit, mono, 16kHz)

        Returns:
            True if sent successfully
        """
        if not self._ws or not self._connected:
            logger.warning("Not connected, cannot send audio")
            return False

        try:
            # Compress audio
            compressed = gzip.compress(audio_data)

            # Build message: [Header 4B] [Sequence 4B] [Payload_Size 4B] [Payload]
            header = self._build_header(
                msg_type=AUDIO_ONLY_REQUEST,
                msg_type_flags=SEQUENCE_POSITIVE,
                serial_method=NO_SERIALIZATION,
                compress_method=GZIP_COMPRESSION,
            )
            self._sequence += 1
            sequence = struct.pack(">i", self._sequence)  # 有符号整数
            payload_size = struct.pack(">I", len(compressed))

            message = header + sequence + payload_size + compressed
            await self._ws.send(message)

            return True

        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            return False

    async def _send_last_audio(self) -> None:
        """Send last audio packet to signal end of stream."""
        if not self._ws:
            return

        try:
            # Build message: [Header 4B] [Sequence 4B] [Payload_Size 4B]
            # Empty payload, last message flag (sequence < 0)
            header = self._build_header(
                msg_type=AUDIO_ONLY_REQUEST,
                msg_type_flags=SEQUENCE_LAST,
                serial_method=NO_SERIALIZATION,
                compress_method=NO_COMPRESSION,
            )
            sequence = struct.pack(">i", -1)  # 负数表示最后一个包
            payload_size = struct.pack(">I", 0)

            message = header + sequence + payload_size
            await self._ws.send(message)

            logger.debug("Sent last audio packet")

        except Exception as e:
            logger.warning(f"Failed to send last packet: {e}")

    async def receive_result(self, timeout: float = 0.1) -> Optional[ASRStreamResult]:
        """
        Receive recognition result.

        Args:
            timeout: Receive timeout in seconds

        Returns:
            ASRStreamResult or None if no result available
        """
        if not self._ws or not self._connected:
            return None

        try:
            data = await asyncio.wait_for(
                self._ws.recv(),
                timeout=timeout,
            )

            return self._parse_response(data)

        except asyncio.TimeoutError:
            # No data available within timeout, this is normal
            return None
        except Exception as e:
            logger.error(f"Failed to receive result: {e}")
            return None

    def _parse_response(self, data: bytes) -> Optional[ASRStreamResult]:
        """Parse binary response from server."""
        if len(data) < 4:
            return None

        # Parse header
        header = struct.unpack(">I", data[:4])[0]

        msg_type = (header >> 20) & 0x0F
        msg_flags = (header >> 16) & 0x0F
        serial_method = (header >> 12) & 0x0F
        compress_method = (header >> 8) & 0x0F

        # Check message type
        if msg_type == SERVER_ERROR:
            self._connected = False  # 标记连接已断开
            error_msg = "Unknown error"
            # SERVER_ERROR 格式: [Header 4B] [Error_Code 4B] [Error_Msg_Len 4B] [Error_Msg UTF8]
            if len(data) >= 12:
                error_code = struct.unpack(">I", data[4:8])[0]
                error_msg_len = struct.unpack(">I", data[8:12])[0]
                if error_msg_len > 0 and len(data) >= 12 + error_msg_len:
                    error_text = data[12:12+error_msg_len].decode('utf-8', errors='ignore')
                    # 尝试解析 JSON 格式的错误消息
                    try:
                        error_json = json.loads(error_text)
                        msg = error_json.get('error', error_json.get('message', error_text))
                        error_msg = f"code={error_code}, {msg}"
                    except json.JSONDecodeError:
                        error_msg = f"code={error_code}, {error_text}"
                else:
                    error_msg = f"code={error_code}"
            logger.error(f"Server error: {error_msg}")
            return None

        if msg_type not in (FULL_SERVER_RESPONSE, SERVER_ACK):
            return None

        # Parse response: [Header 4B] [Sequence 4B] [Payload_Size 4B] [Payload]
        if len(data) < 12:
            return None

        # sequence = struct.unpack(">i", data[4:8])[0]  # 可用于调试
        payload_size = struct.unpack(">I", data[8:12])[0]
        if payload_size == 0:
            return None

        if len(data) < 12 + payload_size:
            return None

        payload = data[12:12+payload_size]

        # Decompress if needed
        if compress_method == GZIP_COMPRESSION:
            try:
                payload = gzip.decompress(payload)
            except Exception as e:
                logger.warning(f"Failed to decompress: {e}")
                return None

        # Parse JSON
        if serial_method == JSON_SERIALIZATION:
            try:
                result = json.loads(payload.decode("utf-8"))
                return self._extract_result(result, msg_flags)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
                return None

        return None

    def _extract_result(self, result: dict, msg_flags: int) -> Optional[ASRStreamResult]:
        """Extract ASR result from parsed response."""
        # Check for result field
        if "result" not in result:
            return None

        res = result.get("result", {})

        # Get text from various possible fields
        text = ""
        if "text" in res:
            text = res["text"]
        elif "utterances" in res and res["utterances"]:
            # Combine all utterances
            texts = [u.get("text", "") for u in res["utterances"]]
            text = "".join(texts)

        if not text:
            return None

        # Check if this is final result
        is_final = msg_flags == SEQUENCE_LAST or msg_flags == SEQUENCE_NEGATIVE

        return ASRStreamResult(
            text=text,
            is_final=is_final,
            confidence=res.get("confidence", 0.9),
            sequence=result.get("sequence", self._sequence),
        )

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected and self._ws is not None

    @property
    def config(self) -> DoubaoStreamingConfig:
        """Get current configuration."""
        return self._config


async def transcribe_audio_stream(
    audio_chunks: List[bytes],
    config: Optional[DoubaoStreamingConfig] = None,
    on_result: Optional[Callable[[ASRStreamResult], None]] = None,
) -> str:
    """
    Transcribe a stream of audio chunks.

    Args:
        audio_chunks: List of PCM audio byte chunks
        config: ASR configuration
        on_result: Callback for each result

    Returns:
        Final transcription text
    """
    final_text = ""

    async with DoubaoStreamingASR(config) as asr:
        for chunk in audio_chunks:
            await asr.send_audio(chunk)

            # Try to receive any available results
            while True:
                result = await asr.receive_result(timeout=0.01)
                if result is None:
                    break

                if on_result:
                    on_result(result)

                if result.is_final:
                    final_text = result.text

            # Small delay between chunks
            await asyncio.sleep(0.01)

        # Receive remaining results
        for _ in range(100):  # Max 10 seconds
            result = await asr.receive_result(timeout=0.1)
            if result is None:
                break

            if on_result:
                on_result(result)

            if result.is_final:
                final_text = result.text

    return final_text
