from fastapi.testclient import TestClient

import app.main as main


def test_production_period_endpoint_is_read_only_and_deterministic():
    client = TestClient(main.app)

    response = client.get("/api/production/periods?as_of=2026-10-16")

    assert response.status_code == 200
    body = response.json()
    assert body["as_of_date"] == "2026-10-16"
    assert body["as_of_source"] == "query"
    assert body["periods"]["today"]["start_date"] == "2026-10-16"
    assert body["periods"]["previous_day"]["end_date"] == "2026-10-15"
    assert body["periods"]["month_to_date"]["end_date"] == "2026-10-16"
    assert body["periods"]["previous_month_to_date"]["end_date"] == "2026-09-16"
    assert body["periods"]["year_to_date"]["start_date"] == "2026-01-01"
    assert body["business_labels"]["sd_hi"]["status"] == (
        "pending_business_confirmation"
    )
    assert body["business_labels"]["sd_bi"]["status"] == (
        "pending_business_confirmation"
    )


def test_production_period_endpoint_rejects_invalid_date():
    response = TestClient(main.app).get(
        "/api/production/periods?as_of=not-a-date"
    )

    assert response.status_code == 422
