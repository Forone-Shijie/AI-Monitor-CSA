"""
Test script for Doubao Streaming ASR.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))


async def test_connection():
    """Test WebSocket connection to Doubao ASR."""
    from src.perception.doubao_streaming_asr import DoubaoStreamingASR, DoubaoStreamingConfig

    print("=" * 50)
    print("Testing Doubao Streaming ASR Connection")
    print("=" * 50)

    # Check environment variables
    app_id = os.environ.get("DOUBAO_APP_ID", "")
    access_key = os.environ.get("DOUBAO_ACCESS_TOKEN", "")
    cluster = os.environ.get("DOUBAO_CLUSTER", "volcengine_streaming_common")

    print(f"\nConfiguration:")
    print(f"  APP_ID: {app_id[:4]}...{app_id[-4:] if len(app_id) > 8 else 'N/A'}")
    print(f"  ACCESS_KEY: {access_key[:4]}...{access_key[-4:] if len(access_key) > 8 else 'N/A'}")
    print(f"  CLUSTER: {cluster}")

    if not app_id or not access_key:
        print("\n[ERROR] Missing DOUBAO_APP_ID or DOUBAO_ACCESS_TOKEN")
        return False

    # Create ASR instance
    config = DoubaoStreamingConfig(
        app_id=app_id,
        access_key=access_key,
        cluster=cluster,
    )

    asr = DoubaoStreamingASR(config)

    # Try to connect
    print("\n[INFO] Attempting to connect...")
    try:
        connected = await asr.connect()
        if connected:
            print("[SUCCESS] WebSocket connection established!")
            print(f"  Connect ID: {asr._connect_id}")

            # Send a small test audio packet (silence)
            silence = bytes(3200)  # 100ms of 16kHz 16-bit mono silence
            print("\n[INFO] Sending test audio packet (silence)...")
            sent = await asr.send_audio(silence)
            print(f"  Sent: {sent}")

            # Try to receive (may timeout, that's ok)
            print("\n[INFO] Waiting for response (1s timeout)...")
            result = await asr.receive_result(timeout=1.0)
            if result:
                print(f"  Result: {result.text}")
            else:
                print("  No result yet (expected for silence)")

            # Disconnect
            print("\n[INFO] Disconnecting...")
            await asr.disconnect()
            print("[SUCCESS] Test completed!")
            return True
        else:
            print("[FAILED] Connection failed")
            return False
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_audio_file():
    """Test ASR with a real audio file if available."""
    from src.perception.doubao_streaming_asr import DoubaoStreamingASR

    # Check for test audio file
    test_files = [
        "tests/test_audio.wav",
        "test_audio.wav",
        "tests/data/test_audio.wav",
    ]

    audio_file = None
    for f in test_files:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f)
        if os.path.exists(path):
            audio_file = path
            break

    if not audio_file:
        print("\n[SKIP] No test audio file found")
        return True

    print(f"\n[INFO] Testing with audio file: {audio_file}")

    try:
        import wave
        with wave.open(audio_file, 'rb') as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            audio_data = wf.readframes(wf.getnframes())

        print(f"  Sample rate: {sample_rate}")
        print(f"  Channels: {channels}")
        print(f"  Sample width: {sample_width}")
        print(f"  Duration: {len(audio_data) / (sample_rate * channels * sample_width):.2f}s")

        async with DoubaoStreamingASR() as asr:
            # Send audio in chunks
            chunk_size = 3200  # 100ms at 16kHz 16-bit
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i+chunk_size]
                await asr.send_audio(chunk)
                await asyncio.sleep(0.1)  # Simulate real-time

                # Check for results
                result = await asr.receive_result(timeout=0.05)
                if result and result.text:
                    print(f"  [RESULT] {result.text} (final={result.is_final})")

            # Wait for final results
            for _ in range(20):
                result = await asr.receive_result(timeout=0.5)
                if result and result.text:
                    print(f"  [FINAL] {result.text}")
                    break

        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


if __name__ == "__main__":
    print("Doubao Streaming ASR Test Suite")
    print("=" * 50)

    success = asyncio.run(test_connection())

    if success:
        asyncio.run(test_with_audio_file())

    print("\n" + "=" * 50)
    print("Test completed")
