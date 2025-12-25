"""
Doubao ASR Engine - 火山引擎豆包大模型流式语音识别.

基于火山引擎官方SDK实现，支持实时流式语音识别。
"""

import asyncio
import gzip
import json
import logging
import os
import struct
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import aiohttp

from .asr_engine import ASREngine, ASRLanguage, ASRResult, ASRSegment, ASRStatus

# 配置日志
logger = logging.getLogger(__name__)


class ProtocolVersion(IntEnum):
    """协议版本."""
    V1 = 0b0001


class MessageType(IntEnum):
    """消息类型."""
    CLIENT_FULL_REQUEST = 0b0001
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010
    SERVER_FULL_RESPONSE = 0b1001
    SERVER_ERROR_RESPONSE = 0b1111


class MessageTypeSpecificFlags(IntEnum):
    """消息类型标志."""
    NO_SEQUENCE = 0b0000
    POS_SEQUENCE = 0b0001
    NEG_SEQUENCE = 0b0010
    NEG_WITH_SEQUENCE = 0b0011


class SerializationType(IntEnum):
    """序列化类型."""
    NO_SERIALIZATION = 0b0000
    JSON = 0b0001


class CompressionType(IntEnum):
    """压缩类型."""
    NO_COMPRESSION = 0b0000
    GZIP = 0b0001


@dataclass
class DoubaoConfig:
    """豆包ASR配置."""

    # 认证信息 (从环境变量读取)
    app_id: str = field(default_factory=lambda: os.getenv("DOUBAO_APP_ID", ""))
    access_token: str = field(default_factory=lambda: os.getenv("DOUBAO_ACCESS_TOKEN", ""))

    # WebSocket地址
    # 双向流式(优化版): wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async (推荐)
    # 双向流式: wss://openspeech.bytedance.com/api/v3/sauc/bigmodel
    # 流式输入: wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream
    ws_url: str = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async"

    # 音频配置
    sample_rate: int = 16000
    bits: int = 16
    channels: int = 1

    # 分段配置 (毫秒)
    segment_duration_ms: int = 200  # 每个音频包的时长

    # 识别配置
    enable_itn: bool = True      # 逆文本正则化
    enable_punc: bool = True     # 标点
    enable_ddc: bool = True      # 口语顺滑
    show_utterances: bool = True # 显示分句

    def validate(self) -> bool:
        """验证配置是否完整."""
        if not self.app_id:
            logger.error("DOUBAO_APP_ID not set")
            return False
        if not self.access_token:
            logger.error("DOUBAO_ACCESS_TOKEN not set")
            return False
        return True


@dataclass
class DoubaoResponse:
    """豆包ASR响应."""
    code: int = 0
    event: int = 0
    is_last_package: bool = False
    payload_sequence: int = 0
    payload_size: int = 0
    payload_msg: Optional[Dict[str, Any]] = None

    @property
    def success(self) -> bool:
        return self.code == 0

    @property
    def text(self) -> str:
        """提取识别文本."""
        if self.payload_msg and "result" in self.payload_msg:
            return self.payload_msg["result"].get("text", "")
        return ""

    @property
    def utterances(self) -> List[Dict]:
        """提取分句信息."""
        if self.payload_msg and "result" in self.payload_msg:
            return self.payload_msg["result"].get("utterances", [])
        return []


class DoubaoASREngine(ASREngine):
    """
    豆包大模型流式语音识别引擎.

    使用火山引擎WebSocket API进行实时语音识别。

    Usage:
        engine = DoubaoASREngine()

        # 流式识别
        async for result in engine.transcribe_stream(audio_chunks):
            print(result.text)
    """

    def __init__(
        self,
        config: Optional[DoubaoConfig] = None,
        language: ASRLanguage = ASRLanguage.CHINESE,
    ) -> None:
        """
        初始化豆包ASR引擎.

        Args:
            config: 豆包配置，默认从环境变量读取
            language: 识别语言
        """
        super().__init__(language)
        self.config = config or DoubaoConfig()

        # 连接状态
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._seq: int = 1
        self._lock = asyncio.Lock()

        # 回调
        self._on_result: Optional[Callable[[str, bool], None]] = None

        # 验证配置
        if self.config.validate():
            self._is_initialized = True
            logger.info("DoubaoASREngine initialized successfully")
        else:
            logger.warning("DoubaoASREngine config incomplete, ASR disabled")

    def _build_header(
        self,
        message_type: int = MessageType.CLIENT_FULL_REQUEST,
        flags: int = MessageTypeSpecificFlags.POS_SEQUENCE,
    ) -> bytes:
        """构建请求头."""
        header = bytearray()
        header.append((ProtocolVersion.V1 << 4) | 1)  # version + header size
        header.append((message_type << 4) | flags)
        header.append((SerializationType.JSON << 4) | CompressionType.GZIP)
        header.append(0x00)  # reserved
        return bytes(header)

    def _build_auth_headers(self) -> Dict[str, str]:
        """构建认证头."""
        return {
            "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
            "X-Api-Request-Id": str(uuid.uuid4()),
            "X-Api-Access-Key": self.config.access_token,
            "X-Api-App-Key": self.config.app_id,
        }

    def _build_full_request(self) -> bytes:
        """构建完整请求 (首包)."""
        header = self._build_header(
            MessageType.CLIENT_FULL_REQUEST,
            MessageTypeSpecificFlags.POS_SEQUENCE,
        )

        payload = {
            "user": {
                "uid": f"cc_sop_{uuid.uuid4().hex[:8]}"
            },
            "audio": {
                "format": "pcm",
                "codec": "raw",
                "rate": self.config.sample_rate,
                "bits": self.config.bits,
                "channel": self.config.channels,
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": self.config.enable_itn,
                "enable_punc": self.config.enable_punc,
                "enable_ddc": self.config.enable_ddc,
                "show_utterances": self.config.show_utterances,
                "enable_nonstream": False,
            }
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        compressed = gzip.compress(payload_bytes)

        request = bytearray()
        request.extend(header)
        request.extend(struct.pack(">i", self._seq))
        request.extend(struct.pack(">I", len(compressed)))
        request.extend(compressed)

        return bytes(request)

    def _build_audio_request(self, audio_data: bytes, is_last: bool = False) -> bytes:
        """构建音频数据请求."""
        seq = self._seq

        if is_last:
            flags = MessageTypeSpecificFlags.NEG_WITH_SEQUENCE
            seq = -seq
        else:
            flags = MessageTypeSpecificFlags.POS_SEQUENCE

        header = self._build_header(
            MessageType.CLIENT_AUDIO_ONLY_REQUEST,
            flags,
        )

        compressed = gzip.compress(audio_data)

        request = bytearray()
        request.extend(header)
        request.extend(struct.pack(">i", seq))
        request.extend(struct.pack(">I", len(compressed)))
        request.extend(compressed)

        return bytes(request)

    def _parse_response(self, data: bytes) -> DoubaoResponse:
        """解析服务器响应."""
        response = DoubaoResponse()

        if len(data) < 4:
            logger.error("Response too short")
            return response

        header_size = data[0] & 0x0f
        message_type = data[1] >> 4
        message_flags = data[1] & 0x0f
        compression = data[2] & 0x0f

        payload = data[header_size * 4:]

        # 解析序列号和标志
        if message_flags & 0x01:  # has sequence
            response.payload_sequence = struct.unpack(">i", payload[:4])[0]
            payload = payload[4:]
        if message_flags & 0x02:  # is last
            response.is_last_package = True
        if message_flags & 0x04:  # has event
            response.event = struct.unpack(">i", payload[:4])[0]
            payload = payload[4:]

        # 解析消息体
        if message_type == MessageType.SERVER_FULL_RESPONSE:
            response.payload_size = struct.unpack(">I", payload[:4])[0]
            payload = payload[4:]
        elif message_type == MessageType.SERVER_ERROR_RESPONSE:
            response.code = struct.unpack(">i", payload[:4])[0]
            response.payload_size = struct.unpack(">I", payload[4:8])[0]
            payload = payload[8:]

        if not payload:
            return response

        # 解压缩
        if compression == CompressionType.GZIP:
            try:
                payload = gzip.decompress(payload)
            except Exception as e:
                logger.error(f"Failed to decompress: {e}")
                return response

        # 解析JSON
        try:
            response.payload_msg = json.loads(payload.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")

        return response

    async def connect(self) -> bool:
        """建立WebSocket连接."""
        if not self._is_initialized:
            logger.error("Engine not initialized, check config")
            return False

        async with self._lock:
            try:
                self._session = aiohttp.ClientSession()
                self._ws = await self._session.ws_connect(
                    self.config.ws_url,
                    headers=self._build_auth_headers(),
                )
                self._seq = 1
                self._status = ASRStatus.IDLE
                logger.info(f"Connected to {self.config.ws_url}")
                return True
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
                await self._cleanup()
                return False

    async def _cleanup(self) -> None:
        """清理连接资源."""
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()
        self._ws = None
        self._session = None
        self._status = ASRStatus.IDLE

    async def start_session(self) -> bool:
        """发送会话开始请求."""
        if not self._ws:
            logger.error("Not connected")
            return False

        try:
            request = self._build_full_request()
            await self._ws.send_bytes(request)
            self._seq += 1

            # 等待响应
            msg = await self._ws.receive()
            if msg.type == aiohttp.WSMsgType.BINARY:
                response = self._parse_response(msg.data)
                if response.success:
                    self._status = ASRStatus.LISTENING
                    logger.info("Session started successfully")
                    return True
                else:
                    logger.error(f"Session start failed: code={response.code}")
            else:
                logger.error(f"Unexpected message type: {msg.type}")

            return False
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return False

    async def send_audio(self, audio_data: bytes, is_last: bool = False) -> None:
        """
        发送音频数据.

        Args:
            audio_data: PCM音频数据 (16-bit, mono)
            is_last: 是否为最后一包
        """
        if not self._ws or self._ws.closed:
            logger.warning("WebSocket not connected, cannot send audio")
            return

        try:
            request = self._build_audio_request(audio_data, is_last)
            await self._ws.send_bytes(request)
            if not is_last:
                self._seq += 1
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")

    async def receive_results(self) -> AsyncGenerator[DoubaoResponse, None]:
        """接收识别结果."""
        if not self._ws:
            return

        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    response = self._parse_response(msg.data)
                    yield response

                    if response.is_last_package or not response.success:
                        break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg.data}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("WebSocket closed")
                    break
        except Exception as e:
            logger.error(f"Error receiving results: {e}")

    async def transcribe_stream(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        on_partial: Optional[Callable[[str], None]] = None,
    ) -> ASRResult:
        """
        流式转录音频.

        Args:
            audio_generator: 异步音频数据生成器
            on_partial: 部分结果回调

        Returns:
            最终ASR结果
        """
        if not await self.connect():
            return ASRResult(
                success=False,
                text="",
                error_message="Failed to connect to Doubao ASR",
            )

        if not await self.start_session():
            await self._cleanup()
            return ASRResult(
                success=False,
                text="",
                error_message="Failed to start ASR session",
            )

        self._status = ASRStatus.PROCESSING
        final_text = ""
        segments: List[ASRSegment] = []

        async def sender():
            """发送音频数据."""
            audio_buffer = bytearray()
            bytes_per_segment = int(
                self.config.sample_rate
                * self.config.channels
                * (self.config.bits // 8)
                * self.config.segment_duration_ms
                / 1000
            )

            try:
                async for chunk in audio_generator:
                    audio_buffer.extend(chunk)

                    # 分段发送
                    while len(audio_buffer) >= bytes_per_segment:
                        segment = bytes(audio_buffer[:bytes_per_segment])
                        audio_buffer = audio_buffer[bytes_per_segment:]
                        await self.send_audio(segment, is_last=False)
                        await asyncio.sleep(self.config.segment_duration_ms / 1000)

                # 发送剩余数据
                if audio_buffer:
                    await self.send_audio(bytes(audio_buffer), is_last=True)
                else:
                    await self.send_audio(b"", is_last=True)

            except Exception as e:
                logger.error(f"Sender error: {e}")

        # 启动发送任务
        sender_task = asyncio.create_task(sender())

        try:
            # 接收结果
            async for response in self.receive_results():
                if response.text:
                    final_text = response.text
                    if on_partial:
                        on_partial(response.text)
                    logger.debug(f"Partial result: {response.text}")

                # 解析分句
                for utt in response.utterances:
                    if utt.get("definite", False):
                        segments.append(ASRSegment(
                            text=utt.get("text", ""),
                            start_time=utt.get("start_time", 0) / 1000,
                            end_time=utt.get("end_time", 0) / 1000,
                            confidence=1.0,
                            language="zh",
                        ))
        finally:
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                pass
            await self._cleanup()

        self._status = ASRStatus.IDLE

        return ASRResult(
            success=True,
            text=final_text,
            segments=segments,
            language="zh",
            confidence=1.0 if final_text else 0.0,
        )

    async def transcribe_bytes(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
    ) -> ASRResult:
        """
        转录音频字节数据.

        Args:
            audio_data: PCM音频数据
            sample_rate: 采样率

        Returns:
            ASR结果
        """
        async def audio_gen():
            yield audio_data

        return await self.transcribe_stream(audio_gen())

    # 实现抽象方法
    def transcribe(
        self,
        audio: "np.ndarray",
        sample_rate: int = 16000,
    ) -> ASRResult:
        """同步转录 (不推荐，请使用异步方法)."""
        # 转换为bytes
        audio_bytes = (audio * 32767).astype("int16").tobytes()
        return asyncio.run(self.transcribe_bytes(audio_bytes, sample_rate))

    def transcribe_file(self, file_path: str) -> ASRResult:
        """从文件转录 (不推荐，请使用异步方法)."""
        import wave

        with wave.open(file_path, "rb") as wf:
            audio_data = wf.readframes(wf.getnframes())
            sample_rate = wf.getframerate()

        return asyncio.run(self.transcribe_bytes(audio_data, sample_rate))

    def release(self) -> None:
        """释放资源."""
        asyncio.run(self._cleanup())
        self._is_initialized = False


class DoubaoStreamingSession:
    """
    豆包流式识别会话管理器 (bigmodel_async 优化版).

    适配双向流式优化模式：
    - 发送和接收完全解耦
    - 只在结果有变化时才返回数据
    - 支持回调机制实时获取结果
    """

    def __init__(
        self,
        config: Optional[DoubaoConfig] = None,
        on_result: Optional[Callable[[str, bool], None]] = None,
    ):
        """
        初始化流式会话.

        Args:
            config: 配置
            on_result: 结果回调 (text, is_final)
        """
        self.config = config or DoubaoConfig()
        self._engine = DoubaoASREngine(self.config)
        self._connected = False
        self._session_started = False
        self._result_queue: asyncio.Queue[DoubaoResponse] = asyncio.Queue()
        self._receiver_task: Optional[asyncio.Task] = None
        self._on_result = on_result

        # 最新的识别结果 (用于累积)
        self._current_text = ""
        self._is_finished = False

    async def start(self) -> bool:
        """启动会话."""
        if not await self._engine.connect():
            return False

        if not await self._engine.start_session():
            await self._engine._cleanup()
            return False

        self._connected = True
        self._session_started = True
        self._current_text = ""
        self._is_finished = False

        # 启动结果接收任务
        self._receiver_task = asyncio.create_task(self._receive_loop())

        logger.info("DoubaoStreamingSession started (async mode)")
        return True

    async def _receive_loop(self) -> None:
        """
        接收结果循环.

        bigmodel_async 模式下只在结果变化时才收到返回。
        """
        try:
            async for response in self._engine.receive_results():
                # 放入队列供轮询
                await self._result_queue.put(response)

                # 更新当前文本
                if response.text:
                    self._current_text = response.text
                    logger.debug(f"ASR partial: {response.text}")

                    # 触发回调
                    if self._on_result:
                        try:
                            self._on_result(response.text, response.is_last_package)
                        except Exception as e:
                            logger.error(f"Result callback error: {e}")

                if response.is_last_package:
                    self._is_finished = True
                    logger.info(f"ASR final: {self._current_text}")
                    break

                if not response.success:
                    logger.error(f"ASR error: code={response.code}")
                    break

        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop error: {e}")

    async def send_audio(self, audio_data: bytes, is_last: bool = False) -> None:
        """
        发送音频数据.

        Args:
            audio_data: PCM音频数据
            is_last: 是否为最后一包
        """
        if not self._connected:
            logger.warning("Session not started")
            return
        await self._engine.send_audio(audio_data, is_last)
        if is_last:
            logger.debug("Sent last audio packet")

    def get_current_text(self) -> str:
        """获取当前累积的识别文本 (非阻塞)."""
        return self._current_text

    @property
    def is_finished(self) -> bool:
        """是否已完成识别."""
        return self._is_finished

    async def get_result(self, timeout: float = 1.0) -> Optional[DoubaoResponse]:
        """
        获取识别结果 (阻塞等待).

        Args:
            timeout: 超时时间（秒）

        Returns:
            识别响应，超时返回None
        """
        try:
            return await asyncio.wait_for(
                self._result_queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    async def get_all_results(self, timeout: float = 0.1) -> List[DoubaoResponse]:
        """
        获取所有待处理的结果 (非阻塞).

        Args:
            timeout: 单次获取超时

        Returns:
            所有待处理的响应列表
        """
        results = []
        while True:
            try:
                result = await asyncio.wait_for(
                    self._result_queue.get(),
                    timeout=timeout
                )
                results.append(result)
            except asyncio.TimeoutError:
                break
        return results

    async def stop(self) -> str:
        """
        停止会话并返回最终结果.

        Returns:
            最终识别文本
        """
        # 取消接收任务
        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass

        # 清理连接
        await self._engine._cleanup()
        self._connected = False
        self._session_started = False

        final_text = self._current_text
        logger.info(f"DoubaoStreamingSession stopped, final: {final_text}")
        return final_text
