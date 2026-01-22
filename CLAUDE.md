# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CC-SOP Monitor (客舱乘务员姿态与操作规范监测系统) - An AI training evaluation system for China Southern Airlines cabin crew. The system monitors crew performance in training simulators through computer vision, action recognition, and speech analysis.

**Current Status**: Core features implemented (Phase 5). Real-time monitoring, video analysis, and multi-person pose detection are functional.

### Implemented Features

- **Real-time Monitoring**: Camera input with WebSocket streaming + skeleton overlay
- **Video Analysis**: Video upload + offline analysis with skeleton visualization
- **Multi-person Pose Detection**: RTMPose-M supporting up to 5 persons simultaneously
- **Speech Recognition**: Doubao ASR streaming recognition with real-time subtitles
- **SOP Timeline**: ECharts-based action sequence timeline visualization

## Technology Stack

- **Backend**: Python 3.10+, FastAPI
- **Pose Detection**: RTMPose-M (MMPose, COCO 17 keypoints, GPU accelerated)
- **Action Recognition**: ST-GCN + LSTM
- **Speech Recognition**: Doubao ASR API (primary) / Whisper (local fallback)
- **Database**: PostgreSQL + Redis
- **Frontend**: Vue 3 + TypeScript, Vite
- **UI Components**: Element Plus
- **Visualization**: ECharts + Three.js (3D skeleton)

## GPU Requirements

- **Minimum**: NVIDIA GPU with 4GB+ VRAM (RTX 2060 or higher)
- **Recommended**: RTX 3090 (24GB) or RTX 4070 Laptop (8GB)
- **CUDA**: 12.x (RTX 50 series requires 12.8+)
- **Performance**: 30+ FPS for 3-person detection on RTX 4070 Laptop

### GPU Architecture Compatibility

| Architecture | GPU Series | CUDA | Special Handling |
|--------------|------------|------|------------------|
| Ampere | RTX 30xx | 12.0+ | Standard install |
| Ada Lovelace | RTX 40xx | 12.0+ | Standard install |
| Blackwell | RTX 50xx (5070/5080/5090) | **12.8+** | Run `scripts/fix_cuda_blackwell.sh` |

**RTX 50 Series (Blackwell) requires**:
- PyTorch nightly with CUDA 12.8
- mmcv compiled from source with `TORCH_CUDA_ARCH_LIST="8.0;8.6;9.0;12.0"`
- GCC < 14.0 for compilation

## Development Commands

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# Run
python -m src.main

# Format & Lint
black backend/src
isort backend/src
mypy backend/src

# Test
pytest
pytest tests/test_pose_detector.py        # Single test file
pytest --cov=src --cov-report=html        # Coverage report
```

### Frontend
```bash
cd frontend
npm install  # or pnpm install

# Run
npm run dev                               # Dev server at localhost:5173

# Format & Lint
npm run lint
npm run format

# Test
npm run test
npm run test:e2e
```

### Docker
```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
```

### Model Download
```bash
bash scripts/download_models.sh
```

### RTX 50 Series (Blackwell) Setup
```bash
# For RTX 5070/5080/5090 users
bash scripts/fix_cuda_blackwell.sh

# This script will:
# 1. Install PyTorch nightly with CUDA 12.8
# 2. Install CUDA toolkit 12.8 via conda
# 3. Install MMPose dependencies
# 4. Compile mmcv from source with sm_120 support
```

## Architecture

The system follows a layered pipeline architecture:

```
Input Layer (Video/Audio) → Synchronizer (Multi-modal Alignment)
    ↓
Perception Layer
├── PoseDetector (RTMPose) → COCO 17 keypoints, angles, pose_type
├── ActionRecognizer (ST-GCN) → action events with timestamps
└── ASR (Doubao/Whisper) → transcribed text with timestamps
    ↓
Analysis Layer
├── SOPAnalyzer → compares action sequences against SOP rules
└── Synchronizer → aligns multi-modal data by timestamp
    ↓
Evaluation Layer
├── PoseScorer (30% weight) → posture deviation scoring
├── ActionScorer (40% weight) → SOP timing compliance
└── CommunicationScorer (30% weight) → speech timeliness/terminology
    ↓
Output Layer
├── ReportGenerator → LLM-powered improvement suggestions
├── LiveFeedback → WebSocket real-time updates
└── Database → PostgreSQL persistence
```

### Key Module Patterns

All perception modules use abstract base classes with concrete implementations:
- `VideoSource` (base) → `CameraInput`, `RTSPInput`, `FileInput`
- `PoseDetector` (base) → `RTMPoseDetector` (GPU, multi-person, COCO 17-point)
- `ActionRecognizer` (base) → `STGCNRecognizer`
- `ASREngine` (base) → `DoubaoASR`, `WhisperASR`

### Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ws/monitor/{session_id}` | WebSocket | Real-time pose streaming |
| `/api/uploads/videos` | POST | Upload video for analysis |
| `/api/uploads/videos/{id}/stream` | GET | Stream video for playback |
| `/api/session/start` | POST | Start monitoring session |
| `/api/report/{session_id}` | GET | Get session report |

## Configuration

- Main config: `backend/config/config.yaml`
- SOP rules: `backend/config/sop_rules.yaml` (defines scenarios, action sequences, time limits)

## Git Conventions

Conventional Commits format:
```
<type>(<scope>): <subject>
```
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Branch strategy: `main` ← `develop` ← `feature/xxx`, `fix/xxx`

## UI Design

HUD-style aviation theme:
- Background: `#0a1628` (deep blue)
- Accent: `#00d4ff` (cyan glow)
- Chinese font: Microsoft YaHei
- English/Numbers: Times New Roman
