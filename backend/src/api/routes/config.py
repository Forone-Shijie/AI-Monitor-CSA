"""
Configuration Routes - API endpoints for system configuration.

Endpoints:
- GET /config - Get system configuration
- PUT /config - Update configuration
- GET /config/scenarios - Get available scenarios
- GET /config/weights - Get evaluation weights
- PUT /config/weights - Update evaluation weights
"""

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from ..schemas import (
    ConfigData,
    ConfigResponse,
    ConfigUpdateRequest,
    ErrorResponse,
    EvaluationWeightsData,
    SOPRuleData,
)

router = APIRouter(prefix="/config", tags=["Configuration"])


# In-memory configuration (in production, use database or config file)
_config = ConfigData(
    sop_rules={
        "brace_position": SOPRuleData(
            scenario_id="brace_position",
            name="防冲击姿势",
            trigger_keywords=["brace", "防冲击", "防冲击姿势"],
            trigger_event="emergency_landing",
            max_total_time=30.0,
            steps=[
                {"step_id": 1, "action": "ACT_001", "name": "弯腰低头", "time_limit": 5.0},
                {"step_id": 2, "action": "ACT_002", "name": "双手抱头", "time_limit": 3.0},
                {"step_id": 3, "action": "ACT_003", "name": "保持姿势", "time_limit": 20.0},
            ],
        ),
        "fire_emergency": SOPRuleData(
            scenario_id="fire_emergency",
            name="火警处置",
            trigger_keywords=["fire", "火警", "着火"],
            trigger_event="fire_alarm",
            max_total_time=60.0,
            steps=[
                {"step_id": 1, "action": "ACT_101", "name": "按压呼叫按钮", "time_limit": 5.0},
                {"step_id": 2, "action": "ACT_102", "name": "提起灭火器", "time_limit": 10.0},
                {"step_id": 3, "action": "ACT_103", "name": "拔除保险销", "time_limit": 5.0},
            ],
        ),
    },
    evaluation_weights=EvaluationWeightsData(
        pose=0.30,
        action=0.40,
        communication=0.30,
    ),
    video_fps=30,
    pose_detection_confidence=0.5,
    asr_mode="auto",
)


@router.get(
    "",
    response_model=ConfigResponse,
    summary="Get configuration",
    description="Get current system configuration",
)
async def get_config() -> ConfigResponse:
    """Get system configuration."""
    return ConfigResponse(
        success=True,
        message="Configuration retrieved",
        data=_config,
    )


@router.put(
    "",
    response_model=ConfigResponse,
    summary="Update configuration",
    description="Update system configuration",
)
async def update_config(request: ConfigUpdateRequest) -> ConfigResponse:
    """Update system configuration."""
    global _config

    if request.evaluation_weights:
        _config.evaluation_weights = request.evaluation_weights

    if request.video_fps is not None:
        _config.video_fps = request.video_fps

    if request.pose_detection_confidence is not None:
        _config.pose_detection_confidence = request.pose_detection_confidence

    if request.asr_mode is not None:
        _config.asr_mode = request.asr_mode

    return ConfigResponse(
        success=True,
        message="Configuration updated",
        data=_config,
    )


@router.get(
    "/scenarios",
    summary="Get available scenarios",
    description="Get list of available training scenarios",
)
async def get_scenarios() -> Dict:
    """Get available scenarios."""
    scenarios = []

    for scenario_id, rule in _config.sop_rules.items():
        scenarios.append({
            "id": scenario_id,
            "name": rule.name,
            "description": f"{len(rule.steps)} steps, max {rule.max_total_time}s",
            "trigger_keywords": rule.trigger_keywords,
            "steps": len(rule.steps),
            "max_time": rule.max_total_time,
        })

    return {
        "success": True,
        "message": "Scenarios retrieved",
        "data": scenarios,
    }


@router.get(
    "/scenarios/{scenario_id}",
    summary="Get scenario details",
    description="Get detailed configuration for a scenario",
)
async def get_scenario(scenario_id: str) -> Dict:
    """Get scenario details."""
    if scenario_id not in _config.sop_rules:
        raise HTTPException(status_code=404, detail="Scenario not found")

    rule = _config.sop_rules[scenario_id]

    return {
        "success": True,
        "message": "Scenario retrieved",
        "data": {
            "id": scenario_id,
            "name": rule.name,
            "trigger_keywords": rule.trigger_keywords,
            "trigger_event": rule.trigger_event,
            "max_total_time": rule.max_total_time,
            "steps": rule.steps,
        },
    }


@router.get(
    "/weights",
    summary="Get evaluation weights",
    description="Get current evaluation weights",
)
async def get_weights() -> Dict:
    """Get evaluation weights."""
    return {
        "success": True,
        "message": "Weights retrieved",
        "data": {
            "pose": _config.evaluation_weights.pose,
            "action": _config.evaluation_weights.action,
            "communication": _config.evaluation_weights.communication,
        },
    }


@router.put(
    "/weights",
    summary="Update evaluation weights",
    description="Update evaluation weights",
)
async def update_weights(weights: EvaluationWeightsData) -> Dict:
    """Update evaluation weights."""
    global _config

    # Normalize weights
    total = weights.pose + weights.action + weights.communication
    if abs(total - 1.0) > 0.01:
        weights.pose /= total
        weights.action /= total
        weights.communication /= total

    _config.evaluation_weights = weights

    return {
        "success": True,
        "message": "Weights updated",
        "data": {
            "pose": weights.pose,
            "action": weights.action,
            "communication": weights.communication,
        },
    }


@router.get(
    "/asr-modes",
    summary="Get ASR modes",
    description="Get available ASR modes",
)
async def get_asr_modes() -> Dict:
    """Get available ASR modes."""
    return {
        "success": True,
        "message": "ASR modes retrieved",
        "data": {
            "current": _config.asr_mode,
            "available": [
                {"id": "auto", "name": "自动", "description": "在线优先，离线备份"},
                {"id": "online", "name": "在线", "description": "仅使用豆包API"},
                {"id": "offline", "name": "离线", "description": "仅使用本地Whisper"},
            ],
        },
    }


@router.put(
    "/asr-mode",
    summary="Set ASR mode",
    description="Set ASR operation mode",
)
async def set_asr_mode(mode: str) -> Dict:
    """Set ASR mode."""
    global _config

    if mode not in ["auto", "online", "offline"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid mode. Must be 'auto', 'online', or 'offline'",
        )

    _config.asr_mode = mode

    return {
        "success": True,
        "message": f"ASR mode set to {mode}",
        "data": {"mode": mode},
    }


def get_current_config() -> ConfigData:
    """Get current configuration (for internal use)."""
    return _config


@router.get(
    "/cameras",
    summary="Get available cameras",
    description="Get list of available video capture devices",
)
async def get_cameras() -> Dict:
    """Get available cameras."""
    cameras = []
    try:
        import cv2

        for i in range(10):  # Check first 10 camera indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append({
                    "id": i,
                    "name": f"摄像头 {i}",
                })
                cap.release()
    except Exception:
        pass

    return {
        "success": True,
        "message": "Cameras retrieved",
        "data": cameras,
    }


@router.get(
    "/audio-devices",
    summary="Get available audio devices",
    description="Get list of available audio input devices",
)
async def get_audio_devices() -> Dict:
    """Get available audio input devices."""
    try:
        from src.input.audio_input import MicrophoneInput
        devices = MicrophoneInput.list_devices()
        # Format devices for frontend
        formatted_devices = [
            {"id": d["id"], "name": d["name"]}
            for d in devices
        ]
        return {
            "success": True,
            "message": "Audio devices retrieved",
            "data": formatted_devices,
        }
    except Exception:
        return {
            "success": True,
            "message": "No audio devices available",
            "data": [],
        }
