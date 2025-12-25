# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CC-SOP Monitor (客舱乘务员姿态与操作规范监测系统) - An AI training evaluation system for China Southern Airlines cabin crew. The system monitors crew performance in training simulators through computer vision, action recognition, and speech analysis.

**Current Status**: Phase 10 - Local AI Deployment. Core system (Phase 0-9) is complete. Now integrating local ASR (FunASR) and LLM (Ollama + Qwen).

## Technology Stack

- **Backend**: Python 3.10+, FastAPI
- **Pose Detection**: MediaPipe Pose (33 keypoints)
- **Action Recognition**: ST-GCN + LSTM
- **Speech Recognition**: FunASR Paraformer (planned)
- **AI Analysis**: Ollama + Qwen2.5 (local LLM, planned)
- **Database**: PostgreSQL + Redis
- **Frontend**: Vue 3 + TypeScript, Vite
- **UI Components**: Element Plus
- **Visualization**: ECharts + Three.js (3D skeleton)

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
├── PoseDetector (MediaPipe) → keypoints, angles, pose_type
├── ActionRecognizer (ST-GCN) → action events with timestamps
└── ASR (FunASR) → transcribed text with timestamps
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
- `PoseDetector` (base) → `MediaPipePose`
- `ActionRecognizer` (base) → `STGCNRecognizer`
- `ASREngine` (base) → `FunASREngine` (planned)

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
