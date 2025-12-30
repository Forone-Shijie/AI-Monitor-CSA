# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CC-SOP Monitor (客舱乘务员姿态与操作规范监测系统) - An AI training evaluation system for China Southern Airlines cabin crew. The system monitors crew performance in training simulators through computer vision, action recognition, and speech analysis.

**Current Status**: Project initialization phase (Phase 0). Documentation and architecture are defined; implementation is pending.

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
- **CUDA**: 12.x
- **Performance**: 30+ FPS for 3-person detection on RTX 4070 Laptop

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
