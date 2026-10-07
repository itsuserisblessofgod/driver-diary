import pytest

from app import service
from app.db import Trip


def trip(id="t1", start="2026-10-01T08:10:00+05:00", end="2026-10-01T08:32:00+05:00",
         amount=2400, payment="card", commission=360):
    return {"id": id, "start": start, "end": end, "amount": amount, "payment": payment, "commission": commission}


def get(client, what, date="2026-10-01"):
    return client.get(f"/api/{what}", params={"date": date}).json()


# --- summary calculation ---

def test_summary_totals_and_payment_split():
    s = service.summarize([
        Trip(amount=2400, commission=360, payment="card"),
        Trip(amount=1500, commission=225, payment="cash"),
        Trip(amount=1000, commission=150, payment="cash"),
    ])
    assert (s["trips"], s["revenue"], s["commission"], s["net"]) == (3, 4900, 735, 4165)
    assert s["by_payment"]["cash"] == {"trips": 2, "revenue": 2500, "commission": 375, "net": 2125}
    assert s["by_payment"]["card"] == {"trips": 1, "revenue": 2400, "commission": 360, "net": 2040}


def test_summary_of_empty_day_is_zeros():
    s = service.summarize([])
    assert s["trips"] == s["revenue"] == s["commission"] == s["net"] == 0
    assert s["by_payment"]["cash"]["trips"] == s["by_payment"]["card"]["trips"] == 0


def test_summary_endpoint_uses_the_days_trips(client):
    client.post("/api/trips", json=trip("t1"))
    client.post("/api/trips", json=trip("t2", "2026-10-01T09:05:00+05:00", "2026-10-01T09:20:00+05:00",
                                        1500, "cash", 225))
    client.post("/api/trips", json=trip("other-day", "2026-10-02T09:05:00+05:00", "2026-10-02T09:20:00+05:00"))
    s = get(client, "summary")
    assert (s["trips"], s["revenue"], s["commission"], s["net"]) == (2, 3900, 585, 3315)
    assert s["by_payment"]["cash"]["net"] == 1275


def test_day_is_local_and_assigned_by_start(client):
    client.post("/api/trips", json=trip("late", "2026-10-01T23:50:00+05:00", "2026-10-02T00:10:00+05:00"))
    client.post("/api/trips", json=trip("early", "2026-10-02T00:20:00+05:00", "2026-10-02T00:40:00+05:00"))
    assert [t["id"] for t in get(client, "trips", "2026-10-01")] == ["late"]
    assert [t["id"] for t in get(client, "trips", "2026-10-02")] == ["early"]


# --- duplicate protection ---

def test_resending_the_same_trip_creates_no_duplicate(client):
    first = client.post("/api/trips", json=trip())
    again = client.post("/api/trips", json=trip())
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json() == first.json()
    assert len(get(client, "trips")) == 1
    assert get(client, "summary")["revenue"] == 2400


def test_same_id_with_different_data_is_a_conflict(client):
    client.post("/api/trips", json=trip())
    assert client.post("/api/trips", json=trip(amount=9999)).status_code == 409
    assert get(client, "trips")[0]["amount"] == 2400


# --- validation ---

@pytest.mark.parametrize("patch", [
    {"amount": 0},
    {"amount": -5},
    {"end": "2026-10-01T08:10:00+05:00"},  # end == start
    {"end": "2026-10-01T08:00:00+05:00"},  # end before start
    {"payment": "crypto"},
    {"commission": 3000},                  # more than the amount
    {"start": "2026-10-01T08:10:00"},      # no timezone
])
def test_invalid_trip_is_rejected(client, patch):
    assert client.post("/api/trips", json={**trip(), **patch}).status_code == 422
    assert get(client, "trips") == []
