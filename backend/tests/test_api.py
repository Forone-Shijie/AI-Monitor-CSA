"""
Phase 7 Tests - API Integration Tests.

Tests for:
- Session management API
- Evaluation and reports API
- Playback API
- Configuration API
- WebSocket endpoints
"""

import pytest
from fastapi.testclient import TestClient

from src.api import app, session_manager


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear sessions before each test."""
    session_manager.clear_all()
    yield
    session_manager.clear_all()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# =============================================================================
# Root and Health Tests
# =============================================================================


class TestRootEndpoints:
    """Tests for root endpoints."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "CC-SOP Monitor API"
        assert data["status"] == "running"

    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "sessions" in data


# =============================================================================
# Session API Tests
# =============================================================================


class TestSessionAPI:
    """Tests for session management API."""

    def test_create_session(self, client):
        """Test session creation."""
        response = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T001",
                "trainee_name": "张三",
                "scenario_id": "brace_position",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["trainee_name"] == "张三"
        assert data["data"]["status"] == "created"

    def test_list_sessions(self, client):
        """Test listing sessions."""
        # Create some sessions
        client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        client.post(
            "/api/sessions",
            json={"trainee_id": "T002", "trainee_name": "李四"},
        )

        response = client.get("/api/sessions")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["total"] == 2
        assert len(data["data"]) == 2

    def test_list_sessions_filter_trainee(self, client):
        """Test filtering sessions by trainee."""
        client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        client.post(
            "/api/sessions",
            json={"trainee_id": "T002", "trainee_name": "李四"},
        )

        response = client.get("/api/sessions?trainee_id=T001")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["trainee_id"] == "T001"

    def test_get_session(self, client):
        """Test getting a session."""
        # Create session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        # Get session
        response = client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["session_id"] == session_id

    def test_get_session_not_found(self, client):
        """Test getting non-existent session."""
        response = client.get("/api/sessions/nonexistent")
        assert response.status_code == 404

    def test_start_session(self, client):
        """Test starting a session."""
        # Create session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        # Start session
        response = client.post(f"/api/sessions/{session_id}/start")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["status"] == "running"

    def test_start_session_not_found(self, client):
        """Test starting non-existent session."""
        response = client.post("/api/sessions/nonexistent/start")
        assert response.status_code == 404

    def test_pause_session(self, client):
        """Test pausing a session."""
        # Create and start session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]
        client.post(f"/api/sessions/{session_id}/start")

        # Pause session
        response = client.post(f"/api/sessions/{session_id}/pause")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["status"] == "paused"

    def test_stop_session(self, client):
        """Test stopping a session."""
        # Create and start session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]
        client.post(f"/api/sessions/{session_id}/start")

        # Stop session
        response = client.post(f"/api/sessions/{session_id}/stop")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["status"] == "completed"

    def test_cancel_session(self, client):
        """Test cancelling a session."""
        # Create session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        # Cancel session
        response = client.post(f"/api/sessions/{session_id}/cancel")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["status"] == "cancelled"

    def test_delete_session(self, client):
        """Test deleting a session."""
        # Create session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        # Delete session
        response = client.delete(f"/api/sessions/{session_id}")
        assert response.status_code == 200

        # Verify deleted
        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_get_monitoring_status(self, client):
        """Test getting monitoring status."""
        # Create and start session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]
        client.post(f"/api/sessions/{session_id}/start")

        # Get status
        response = client.get(f"/api/sessions/{session_id}/status")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["is_running"] is True


# =============================================================================
# Configuration API Tests
# =============================================================================


class TestConfigAPI:
    """Tests for configuration API."""

    def test_get_config(self, client):
        """Test getting configuration."""
        response = client.get("/api/config")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "sop_rules" in data["data"]
        assert "evaluation_weights" in data["data"]

    def test_update_config(self, client):
        """Test updating configuration."""
        response = client.put(
            "/api/config",
            json={
                "video_fps": 60,
                "asr_mode": "offline",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["video_fps"] == 60
        assert data["data"]["asr_mode"] == "offline"

    def test_get_scenarios(self, client):
        """Test getting scenarios."""
        response = client.get("/api/config/scenarios")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 2

    def test_get_scenario(self, client):
        """Test getting specific scenario."""
        response = client.get("/api/config/scenarios/brace_position")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["id"] == "brace_position"
        assert data["data"]["name"] == "防冲击姿势"

    def test_get_scenario_not_found(self, client):
        """Test getting non-existent scenario."""
        response = client.get("/api/config/scenarios/nonexistent")
        assert response.status_code == 404

    def test_get_weights(self, client):
        """Test getting evaluation weights."""
        response = client.get("/api/config/weights")
        assert response.status_code == 200

        data = response.json()
        assert "pose" in data["data"]
        assert "action" in data["data"]
        assert "communication" in data["data"]

    def test_update_weights(self, client):
        """Test updating evaluation weights."""
        response = client.put(
            "/api/config/weights",
            json={
                "pose": 0.4,
                "action": 0.3,
                "communication": 0.3,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["pose"] == 0.4

    def test_get_asr_modes(self, client):
        """Test getting ASR modes."""
        response = client.get("/api/config/asr-modes")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["current"] in ["auto", "online", "offline"]
        assert len(data["data"]["available"]) == 3

    def test_set_asr_mode(self, client):
        """Test setting ASR mode."""
        response = client.put("/api/config/asr-mode?mode=offline")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["mode"] == "offline"

    def test_set_asr_mode_invalid(self, client):
        """Test setting invalid ASR mode."""
        response = client.put("/api/config/asr-mode?mode=invalid")
        assert response.status_code == 400


# =============================================================================
# Playback API Tests
# =============================================================================


class TestPlaybackAPI:
    """Tests for playback API."""

    def test_get_playback_not_found(self, client):
        """Test getting playback for non-existent session."""
        response = client.get("/api/playback/nonexistent")
        assert response.status_code == 404

    def test_get_playback(self, client):
        """Test getting playback data."""
        # Create session with data
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        # Get playback
        response = client.get(f"/api/playback/{session_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["session_id"] == session_id
        assert "frames" in data["data"]

    def test_get_timeline(self, client):
        """Test getting timeline."""
        # Create session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        # Get timeline
        response = client.get(f"/api/playback/{session_id}/timeline")
        assert response.status_code == 200

        data = response.json()
        assert "events" in data["data"]

    def test_get_summary(self, client):
        """Test getting session summary."""
        # Create session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        # Get summary
        response = client.get(f"/api/playback/{session_id}/summary")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["session_id"] == session_id
        assert "statistics" in data["data"]


# =============================================================================
# Evaluation API Tests
# =============================================================================


class TestEvaluationAPI:
    """Tests for evaluation API."""

    def test_get_evaluation_not_found(self, client):
        """Test getting evaluation for non-existent session."""
        response = client.get("/api/evaluation/nonexistent")
        assert response.status_code == 404

    def test_get_evaluation_no_data(self, client):
        """Test getting evaluation when not available."""
        # Create session without evaluation
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        response = client.get(f"/api/evaluation/{session_id}")
        assert response.status_code == 404

    def test_run_evaluation_no_data(self, client):
        """Test running evaluation without data."""
        # Create session without monitoring data
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        response = client.post(f"/api/evaluation/{session_id}/run")
        assert response.status_code == 400

    def test_list_reports(self, client):
        """Test listing reports."""
        response = client.get("/api/reports")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_report_not_found(self, client):
        """Test getting report for session without report."""
        # Create session without report
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        response = client.get(f"/api/reports/{session_id}")
        assert response.status_code == 404


# =============================================================================
# Session Manager Tests
# =============================================================================


class TestSessionManager:
    """Tests for session manager."""

    def test_create_session(self):
        """Test creating session."""
        session = session_manager.create_session(
            trainee_id="T001",
            trainee_name="张三",
            scenario_id="brace_position",
        )

        assert session.trainee_name == "张三"
        assert session.scenario_id == "brace_position"

    def test_get_session(self):
        """Test getting session."""
        created = session_manager.create_session(
            trainee_id="T001",
            trainee_name="张三",
        )

        session = session_manager.get_session(created.session_id)
        assert session is not None
        assert session.session_id == created.session_id

    def test_start_stop_session(self):
        """Test session lifecycle."""
        session = session_manager.create_session(
            trainee_id="T001",
            trainee_name="张三",
        )

        # Start
        assert session_manager.start_session(session.session_id)
        updated = session_manager.get_session(session.session_id)
        assert updated.status.value == "running"

        # Stop
        assert session_manager.stop_session(session.session_id)
        updated = session_manager.get_session(session.session_id)
        assert updated.status.value == "completed"

    def test_add_frame_data(self):
        """Test adding frame data."""
        session = session_manager.create_session(
            trainee_id="T001",
            trainee_name="张三",
        )
        session_manager.start_session(session.session_id)

        frame = session_manager.add_frame_data(
            session.session_id,
            pose={"timestamp": 0.0, "detected": True, "confidence": 0.9},
        )

        assert frame is not None
        assert frame.frame_number == 1

    def test_monitoring_status(self):
        """Test getting monitoring status."""
        session = session_manager.create_session(
            trainee_id="T001",
            trainee_name="张三",
        )
        session_manager.start_session(session.session_id)

        status = session_manager.get_monitoring_status(session.session_id)

        assert status is not None
        assert status.is_running is True


# =============================================================================
# WebSocket Tests
# =============================================================================


class TestWebSocket:
    """Tests for WebSocket endpoints."""

    def test_websocket_connect_invalid_session(self, client):
        """Test WebSocket with invalid session."""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/ws/live/nonexistent"):
                pass

    def test_websocket_connect_valid_session(self, client):
        """Test WebSocket with valid session."""
        # Create session
        create_resp = client.post(
            "/api/sessions",
            json={"trainee_id": "T001", "trainee_name": "张三"},
        )
        session_id = create_resp.json()["data"]["session_id"]

        # Connect WebSocket
        with client.websocket_connect(f"/api/ws/live/{session_id}") as ws:
            # Should receive connected message
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert data["data"]["session_id"] == session_id


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_session_workflow(self, client):
        """Test complete session workflow."""
        # 1. Create session
        create_resp = client.post(
            "/api/sessions",
            json={
                "trainee_id": "T001",
                "trainee_name": "张三",
                "scenario_id": "brace_position",
            },
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["data"]["session_id"]

        # 2. Start monitoring
        start_resp = client.post(f"/api/sessions/{session_id}/start")
        assert start_resp.status_code == 200
        assert start_resp.json()["data"]["status"] == "running"

        # 3. Check status
        status_resp = client.get(f"/api/sessions/{session_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["data"]["is_running"] is True

        # 4. Stop monitoring
        stop_resp = client.post(f"/api/sessions/{session_id}/stop")
        assert stop_resp.status_code == 200
        assert stop_resp.json()["data"]["status"] == "completed"

        # 5. Get summary
        summary_resp = client.get(f"/api/playback/{session_id}/summary")
        assert summary_resp.status_code == 200

    def test_config_workflow(self, client):
        """Test configuration workflow."""
        # 1. Get current config
        config_resp = client.get("/api/config")
        assert config_resp.status_code == 200

        # 2. Get scenarios
        scenarios_resp = client.get("/api/config/scenarios")
        assert scenarios_resp.status_code == 200
        assert len(scenarios_resp.json()["data"]) >= 2

        # 3. Update weights
        weights_resp = client.put(
            "/api/config/weights",
            json={"pose": 0.35, "action": 0.35, "communication": 0.30},
        )
        assert weights_resp.status_code == 200

        # 4. Verify update
        verify_resp = client.get("/api/config/weights")
        assert verify_resp.json()["data"]["pose"] == 0.35


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
