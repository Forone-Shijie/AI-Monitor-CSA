#!/usr/bin/env python3
"""
RTMPose Performance Benchmark Script.

Measures FPS and latency for RTMPose detector on different GPU devices.

Usage:
    python scripts/benchmark_pose.py
    python scripts/benchmark_pose.py --device cuda:0 --num-frames 200
    python scripts/benchmark_pose.py --resolution 1920x1080 --num-persons 3
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="RTMPose Performance Benchmark")
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        help="Device to run benchmark (cuda:0, cuda:1, cpu)",
    )
    parser.add_argument(
        "--num-frames",
        type=int,
        default=100,
        help="Number of frames to benchmark",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=10,
        help="Number of warmup frames",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default="1920x1080",
        help="Frame resolution (e.g., 1920x1080, 1280x720)",
    )
    parser.add_argument(
        "--num-persons",
        type=int,
        default=1,
        help="Expected number of persons (for reporting)",
    )
    return parser.parse_args()


def create_test_frame(width: int, height: int) -> np.ndarray:
    """Create a random test frame."""
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)


def run_benchmark(
    device: str,
    num_frames: int,
    warmup: int,
    width: int,
    height: int,
) -> dict:
    """
    Run benchmark and return results.

    Returns:
        Dictionary with fps, latency_mean, latency_std, latency_min, latency_max
    """
    from perception.rtmpose_detector import RTMPoseDetector

    print(f"\n{'='*60}")
    print(f"RTMPose Performance Benchmark")
    print(f"{'='*60}")
    print(f"Device:      {device}")
    print(f"Resolution:  {width}x{height}")
    print(f"Warmup:      {warmup} frames")
    print(f"Benchmark:   {num_frames} frames")
    print(f"{'='*60}\n")

    # Initialize detector
    print("Initializing RTMPose detector...")
    try:
        detector = RTMPoseDetector(
            device=device,
            det_score_thr=0.3,
            pose_score_thr=0.3,
            max_persons=5,
        )
    except Exception as e:
        print(f"Failed to initialize detector: {e}")
        return None

    print(f"Detector initialized on: {detector.device}")

    # Create test frame
    frame = create_test_frame(width, height)

    # Warmup
    print(f"\nWarming up ({warmup} frames)...")
    for i in range(warmup):
        _ = detector.detect_multi(frame)
        if (i + 1) % 5 == 0:
            print(f"  Warmup: {i + 1}/{warmup}")

    # Benchmark
    print(f"\nRunning benchmark ({num_frames} frames)...")
    latencies = []

    for i in range(num_frames):
        start = time.perf_counter()
        result = detector.detect_multi(frame)
        end = time.perf_counter()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

        if (i + 1) % 20 == 0:
            current_fps = 1000.0 / np.mean(latencies[-20:])
            print(f"  Frame {i + 1}/{num_frames}: {current_fps:.1f} FPS, "
                  f"Persons detected: {result.num_persons}")

    # Calculate statistics
    latencies = np.array(latencies)
    mean_latency = np.mean(latencies)
    std_latency = np.std(latencies)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)
    p95_latency = np.percentile(latencies, 95)
    fps = 1000.0 / mean_latency

    # Release detector
    detector.release()

    # Results
    results = {
        "device": device,
        "resolution": f"{width}x{height}",
        "num_frames": num_frames,
        "fps": fps,
        "latency_mean": mean_latency,
        "latency_std": std_latency,
        "latency_min": min_latency,
        "latency_max": max_latency,
        "latency_p95": p95_latency,
    }

    return results


def print_results(results: dict):
    """Print benchmark results."""
    print(f"\n{'='*60}")
    print("BENCHMARK RESULTS")
    print(f"{'='*60}")
    print(f"Device:          {results['device']}")
    print(f"Resolution:      {results['resolution']}")
    print(f"Frames:          {results['num_frames']}")
    print(f"{'='*60}")
    print(f"FPS:             {results['fps']:.2f}")
    print(f"Latency Mean:    {results['latency_mean']:.2f} ms")
    print(f"Latency Std:     {results['latency_std']:.2f} ms")
    print(f"Latency Min:     {results['latency_min']:.2f} ms")
    print(f"Latency Max:     {results['latency_max']:.2f} ms")
    print(f"Latency P95:     {results['latency_p95']:.2f} ms")
    print(f"{'='*60}")

    # Performance assessment
    print("\nPerformance Assessment:")
    if results['fps'] >= 30:
        print(f"  ✅ Real-time capable ({results['fps']:.0f} FPS >= 30 FPS)")
    else:
        print(f"  ⚠️  Below real-time ({results['fps']:.0f} FPS < 30 FPS)")

    if results['latency_mean'] < 50:
        print(f"  ✅ Low latency ({results['latency_mean']:.0f} ms < 50 ms)")
    elif results['latency_mean'] < 100:
        print(f"  ⚠️  Moderate latency ({results['latency_mean']:.0f} ms)")
    else:
        print(f"  ❌ High latency ({results['latency_mean']:.0f} ms)")


def main():
    """Main entry point."""
    args = parse_args()

    # Parse resolution
    try:
        width, height = map(int, args.resolution.split("x"))
    except ValueError:
        print(f"Invalid resolution format: {args.resolution}")
        print("Expected format: WIDTHxHEIGHT (e.g., 1920x1080)")
        sys.exit(1)

    # Run benchmark
    results = run_benchmark(
        device=args.device,
        num_frames=args.num_frames,
        warmup=args.warmup,
        width=width,
        height=height,
    )

    if results:
        print_results(results)
    else:
        print("\nBenchmark failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
