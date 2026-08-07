from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_http_vertical_slice():
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "catalog_mode": "demo", "engine": "deterministic"}

    analysis = client.post(
        "/api/change/analyze",
        json={"asset_id": "customer_360", "kind": "rename", "column": "customer_id", "new_name": "buyer_id"},
    )
    assert analysis.status_code == 200
    assert len(analysis.json()["known_affected_consumers"]) >= 4

    package = client.post(
        "/api/change/package",
        json={"asset_id": "customer_360", "kind": "rename", "column": "customer_id", "new_name": "buyer_id"},
    )
    assert package.status_code == 200
    assert package.json()["review_status"] == "human_review_required"
    assert len(package.json()["files"]) == 4
