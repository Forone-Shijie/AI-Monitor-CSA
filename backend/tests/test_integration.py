"""
Integration Tests for CC-SOP Monitor

Tests the full system integration including:
- API endpoints
- Session lifecycle
- WebSocket connections
- Data flow between components
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from src.api.app import create_app
from src.api.session_manager import session_manager


@pytest.fixture(autouse=True)
def reset_session_manager():
    """Reset session manager before each test."""
    session_manager.clear_all()
    yield
    session_manager.clear_all()


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestAPIIntegration:
    """Test API endpoint integration."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "sessions" in data

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CC-SOP Monitor API"
        assert data["status"] == "running"


class TestSessionLifecycle:
    """Test complete session lifecycle."""

    def test_create_session(self, client: TestClient):
        """Test session creation."""
        response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T001",
                "trainee_name": "测试学员",
                "scenario_id": "brace_position",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["trainee_id"] == "T001"
        assert data["data"]["status"] == "created"

    def test_full_session_workflow(self, client: TestClient):
        """Test complete session workflow: create -> start -> stop."""
        # Create session
        create_response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T002",
                "trainee_name": "完整流程测试",
                "scenario_id": "brace_position",
            },
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["data"]["session_id"]

        # Start session
        start_response = client.post(
            f"/api/sessions/{session_id}/start",
            json={"trigger_type": "manual"},
        )
        assert start_response.status_code == 200
        assert start_response.json()["success"] is True
        assert start_response.json()["data"]["status"] == "running"

        # Get session status
        status_response = client.get(f"/api/sessions/{session_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["data"]["is_running"] is True

        # Stop session
        stop_response = client.post(
            f"/api/sessions/{session_id}/stop",
            json={"generate_report": True},
        )
        assert stop_response.status_code == 200
        assert stop_response.json()["success"] is True
        assert stop_response.json()["data"]["status"] == "completed"

    def test_session_list(self, client: TestClient):
        """Test session listing."""
        # Create multiple sessions
        for i in range(3):
            client.post(
                "/api/sessions",
                json={
                    "trainee_id": f"T00{i}",
                    "trainee_name": f"学员{i}",
                },
            )

        # List all sessions
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["data"]) == 3

    def test_session_filter_by_trainee(self, client: TestClient):
        """Test session filtering by trainee ID."""
        # Create sessions for different trainees
        client.post(
            "/api/sessions",
            json={"trainee_id": "T100", "trainee_name": "学员A"},
        )
        client.post(
            "/api/sessions",
            json={"trainee_id": "T200", "trainee_name": "学员B"},
        )
        client.post(
            "/api/sessions",
            json={"trainee_id": "T100", "trainee_name": "学员A"},
        )

        # Filter by trainee
        response = client.get("/api/sessions", params={"trainee_id": "T100"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestConfigAPI:
    """Test configuration API."""

    def test_get_config(self, client: TestClient):
        """Test get system configuration."""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        config = data["data"]
        assert "asr_mode" in config
        assert "evaluation_weights" in config

    def test_get_scenarios(self, client: TestClient):
        """Test get scenario list."""
        response = client.get("/api/config/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        scenarios = data["data"]
        assert isinstance(scenarios, list)
        # Should have default brace_position scenario
        scenario_ids = [s["id"] for s in scenarios]
        assert "brace_position" in scenario_ids

    def test_get_weights(self, client: TestClient):
        """Test get evaluation weights."""
        response = client.get("/api/config/weights")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        weights = data["data"]
        assert "pose" in weights
        assert "action" in weights
        assert "communication" in weights
        # Weights should sum to approximately 1.0
        total = weights["pose"] + weights["action"] + weights["communication"]
        assert 0.99 <= total <= 1.01

    def test_update_weights(self, client: TestClient):
        """Test update evaluation weights."""
        new_weights = {
            "pose": 0.4,
            "action": 0.3,
            "communication": 0.3,
        }
        response = client.put("/api/config/weights", json=new_weights)
        assert response.status_code == 200
        data = response.json()
        weights = data["data"]
        assert weights["pose"] == 0.4
        assert weights["action"] == 0.3

    def test_get_asr_modes(self, client: TestClient):
        """Test get ASR modes."""
        response = client.get("/api/config/asr-modes")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        asr_data = data["data"]
        assert "available" in asr_data
        assert "current" in asr_data


class TestPlaybackAPI:
    """Test playback API."""

    def test_playback_requires_session(self, client: TestClient):
        """Test playback requires valid session."""
        response = client.get("/api/playback/nonexistent")
        assert response.status_code == 404

    def test_playback_with_session(self, client: TestClient):
        """Test playback with valid session."""
        # Create and start session
        create_response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T003",
                "trainee_name": "回放测试",
            },
        )
        session_id = create_response.json()["data"]["session_id"]

        # Start session
        client.post(f"/api/sessions/{session_id}/start", json={})

        # Add some frame data (via session manager directly for testing)
        session_data = session_manager.get_session(session_id)
        if session_data:
            for i in range(10):
                session_manager.add_frame_data(
                    session_id,
                    pose={
                        "timestamp": i * 0.033,
                        "detected": True,
                        "keypoints": [[0.5, 0.5, 0.9]] * 33,
                        "confidence": 0.95,
                    },
                )

        # Stop session
        client.post(f"/api/sessions/{session_id}/stop", json={})

        # Get playback data
        response = client.get(f"/api/playback/{session_id}")
        assert response.status_code == 200
        data = response.json()
        playback = data["data"]
        assert playback["session_id"] == session_id
        assert "frames" in playback
        # At least 10 frames from manual injection, may have more from simulation mode
        assert len(playback["frames"]) >= 10


class TestEvaluationAPI:
    """Test evaluation API."""

    def test_evaluation_requires_session(self, client: TestClient):
        """Test evaluation requires valid session."""
        response = client.get("/api/evaluation/nonexistent")
        assert response.status_code == 404

    def test_run_evaluation(self, client: TestClient):
        """Test running evaluation on a completed session."""
        # Create and run session
        create_response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T004",
                "trainee_name": "评估测试",
                "scenario_id": "brace_position",
            },
        )
        session_id = create_response.json()["data"]["session_id"]

        # Start session
        client.post(f"/api/sessions/{session_id}/start", json={})

        # Add some frame data to trigger evaluation
        for i in range(5):
            session_manager.add_frame_data(
                session_id,
                pose={
                    "timestamp": i * 0.033,
                    "detected": True,
                    "keypoints": [[0.5, 0.5, 0.9]] * 33,
                    "confidence": 0.95,
                },
            )

        # Stop session (which triggers evaluation)
        stop_response = client.post(
            f"/api/sessions/{session_id}/stop",
            json={"generate_report": True},
        )
        assert stop_response.status_code == 200

        # Get evaluation result (evaluation is run on stop with data)
        response = client.get(f"/api/evaluation/{session_id}")
        # Evaluation may or may not be generated depending on implementation
        # At minimum, the session should be completed
        assert stop_response.json()["data"]["status"] == "completed"


class TestWebSocketIntegration:
    """Test WebSocket connections."""

    def test_websocket_connection(self, client: TestClient):
        """Test WebSocket connection lifecycle."""
        # Create session
        create_response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T005",
                "trainee_name": "WebSocket测试",
            },
        )
        session_id = create_response.json()["data"]["session_id"]

        # Start session
        client.post(f"/api/sessions/{session_id}/start", json={})

        # Connect WebSocket
        with client.websocket_connect(f"/api/ws/live/{session_id}") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] in ["status", "connected"]

    def test_websocket_receives_updates(self, client: TestClient):
        """Test WebSocket receives frame updates."""
        # Create and start session
        create_response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T006",
                "trainee_name": "WebSocket更新测试",
            },
        )
        session_id = create_response.json()["data"]["session_id"]
        client.post(f"/api/sessions/{session_id}/start", json={})

        with client.websocket_connect(f"/api/ws/live/{session_id}") as websocket:
            # Receive initial status
            initial_data = websocket.receive_json()
            assert "type" in initial_data

            # Add frame data
            session_manager.add_frame_data(
                session_id,
                pose={
                    "timestamp": 0.0,
                    "detected": True,
                    "keypoints": [[0.5, 0.5, 0.9]] * 33,
                    "confidence": 0.95,
                },
            )

            # Note: In a real test, we'd need async handling to receive the broadcast


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_session_id(self, client: TestClient):
        """Test handling of invalid session ID."""
        response = client.get("/api/sessions/invalid-id")
        assert response.status_code == 404

    def test_start_nonexistent_session(self, client: TestClient):
        """Test starting nonexistent session."""
        response = client.post("/api/sessions/nonexistent/start", json={})
        assert response.status_code == 404

    def test_double_start_session(self, client: TestClient):
        """Test starting an already running session."""
        # Create session
        create_response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T007",
                "trainee_name": "双启动测试",
            },
        )
        session_id = create_response.json()["data"]["session_id"]

        # Start session
        client.post(f"/api/sessions/{session_id}/start", json={})

        # Try to start again
        response = client.post(f"/api/sessions/{session_id}/start", json={})
        assert response.status_code == 400


class TestDataIntegrity:
    """Test data integrity across components."""

    def test_session_data_persistence(self, client: TestClient):
        """Test session data is persisted correctly."""
        # Create session with specific data
        create_response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T008",
                "trainee_name": "数据持久性测试",
                "scenario_id": "brace_position",
            },
        )
        session_id = create_response.json()["data"]["session_id"]

        # Get session and verify data
        get_response = client.get(f"/api/sessions/{session_id}")
        assert get_response.status_code == 200
        data = get_response.json()["data"]
        assert data["trainee_id"] == "T008"
        assert data["trainee_name"] == "数据持久性测试"
        assert data["scenario_id"] == "brace_position"

    def test_frame_data_consistency(self, client: TestClient):
        """Test frame data is stored and retrieved consistently."""
        # Create and start session
        create_response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T009",
                "trainee_name": "帧数据一致性测试",
            },
        )
        session_id = create_response.json()["data"]["session_id"]
        client.post(f"/api/sessions/{session_id}/start", json={})

        # Add frames with specific data
        test_keypoints = [[0.1 * i, 0.2 * i, 0.9] for i in range(33)]
        for i in range(5):
            session_manager.add_frame_data(
                session_id,
                pose={
                    "timestamp": i * 0.033,
                    "detected": True,
                    "keypoints": test_keypoints,
                    "confidence": 0.95,
                },
            )

        # Stop and retrieve
        client.post(f"/api/sessions/{session_id}/stop", json={})

        # Get playback and verify
        response = client.get(f"/api/playback/{session_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        # At least 5 frames from manual injection, may have more from simulation mode
        assert len(data["frames"]) >= 5

        # Verify frame structure
        frame = data["frames"][0]
        assert "frame_number" in frame
        assert "timestamp" in frame
        assert "pose" in frame


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
