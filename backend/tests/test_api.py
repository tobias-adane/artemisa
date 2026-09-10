from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_reports_mock_store_and_unconfigured_services():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["store"] == "InMemoryStore"
    assert body["openai_configured"] is False


def test_test_connection_reports_failure_for_unreachable_host():
    resp = client.post(
        "/spaces/test-connection",
        json={"user_id": "00000000-0000-0000-0000-000000000000", "name": "Test", "camera_url": "rtsp://192.0.2.1:554/stream"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error_message"]


def test_test_connection_rejects_malformed_url():
    resp = client.post(
        "/spaces/test-connection",
        json={"user_id": "00000000-0000-0000-0000-000000000000", "name": "Test", "camera_url": "not-a-url"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


def test_me_returns_demo_user():
    resp = client.get("/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "tomas@artemisa.app"
    assert "id" in body


def test_list_spaces_never_leaks_camera_url():
    user_id = client.get("/me").json()["id"]
    resp = client.get("/spaces", params={"user_id": user_id})
    assert resp.status_code == 200
    spaces = resp.json()
    assert len(spaces) >= 1
    for space in spaces:
        assert "camera_url" not in space


def test_create_space_roundtrip_and_no_camera_url_leak():
    user_id = client.get("/me").json()["id"]
    resp = client.post(
        "/spaces",
        json={"user_id": user_id, "name": "Pasillo", "camera_url": "rtsp://192.168.1.50/stream"},
    )
    assert resp.status_code == 200
    created = resp.json()
    assert created["name"] == "Pasillo"
    assert "camera_url" not in created

    listed = client.get("/spaces", params={"user_id": user_id}).json()
    assert any(s["id"] == created["id"] for s in listed)


def test_create_and_list_contact_roundtrip():
    user_id = "11111111-1111-1111-1111-111111111111"
    resp = client.post(
        "/contacts",
        json={"user_id": user_id, "name": "Marcos Ferrari", "phone": "+5491133445566", "relationship": "neighbor", "priority": 5},
    )
    assert resp.status_code == 200
    created = resp.json()
    assert created["confirmed"] is False

    listed = client.get("/contacts", params={"user_id": user_id}).json()
    assert any(c["id"] == created["id"] for c in listed)
