from app.routers import trips as trips_module


def manifest_row(world, color="verde"):
    data = world.client.get(f"/api/v1/trips/{world.trip_id}/manifest", headers=world.auth["admin"]).json()
    return next(r for r in data["rows"] if r["color"] == color)


# ---------- flujo básico (v0.1.7: el pesaje registra recepción + peso) ----------

def test_happy_path_counts(world):
    assert world.scan("pickup").json()["registered_count"] == 1
    assert world.scan("pickup").json()["registered_count"] == 2

    r = world.weigh(kg="12.250")
    assert r.status_code == 200
    assert r.json()["weighed_count"] == 1 and r.json()["limit_count"] == 2

    row = manifest_row(world)
    assert (row["pickup_count"], row["plant_count"], row["weighed_count"]) == (2, 1, 1)


def test_independent_plant_scan_is_rejected(world):
    world.scan("pickup")
    r = world.scan("plant")
    assert r.status_code == 409 and "pesaje" in r.json()["detail"]


def test_weighing_requires_pickup(world):
    r = world.weigh()
    assert r.status_code == 409 and "no tiene bolsas recolectadas" in r.json()["detail"]


def test_weighing_quota_is_enforced(world):
    world.scan("pickup")
    assert world.weigh().status_code == 200
    r = world.weigh()
    assert r.status_code == 409 and "Ya se pesaron 1 de 1" in r.json()["detail"]


def test_weighing_wrong_company_is_rejected_and_registers_nothing(world):
    world.scan("pickup")
    r = world.weigh(company_id=world.company_id + 100)
    assert r.status_code == 409 and "EMPRESA INCORRECTA" in r.json()["detail"]
    assert manifest_row(world)["weighed_count"] == 0


def test_roles_are_enforced(world):
    assert world.scan("pickup", role="plant").status_code == 403
    world.scan("pickup")
    assert world.weigh(role="collector").status_code == 403


# ---------- punto 7: retiros congelados una vez que la planta empieza ----------

def test_first_weighing_moves_trip_to_arrived(world):
    world.scan("pickup")
    world.weigh()
    trip = next(t for t in world.client.get("/api/v1/trips", headers=world.auth["admin"]).json() if t["id"] == world.trip_id)
    assert trip["status"] == "arrived"


def test_pickup_rejected_once_trip_is_arrived(world):
    world.scan("pickup")
    assert world.weigh().status_code == 200  # open -> arrived
    r = world.scan("pickup")
    assert r.status_code == 409 and "recepción de planta" in r.json()["detail"]


def test_pickup_other_color_also_rejected_after_arrival(world):
    world.scan("pickup", color="verde")
    world.weigh(color="verde")
    assert world.scan("pickup", color="azul").status_code == 409


def test_pickup_still_allowed_while_trip_is_open(world):
    for _ in range(3):
        assert world.scan("pickup").status_code == 200


def test_retry_of_pickup_after_arrival_still_returns_original(world):
    first = world.scan("pickup", event="evt-retry-01")
    world.weigh()
    retry = world.scan("pickup", event="evt-retry-01")
    assert retry.status_code == 200
    assert retry.json()["event_id"] == first.json()["event_id"]


# ---------- punto 6: idempotencia y carrera ----------

def test_scan_retry_is_idempotent(world):
    a = world.scan("pickup", event="evt-same-01")
    b = world.scan("pickup", event="evt-same-01")
    assert a.status_code == b.status_code == 200
    assert a.json()["event_id"] == b.json()["event_id"]
    assert world.scan("pickup").json()["registered_count"] == 2  # solo 1 evento previo


def test_weighing_retry_is_idempotent(world):
    world.scan("pickup")
    a = world.weigh(event="evt-w-0001")
    b = world.weigh(event="evt-w-0001")
    assert a.status_code == b.status_code == 200
    assert a.json()["weighing_id"] == b.json()["weighing_id"]
    assert manifest_row(world)["weighed_count"] == 1


def test_lock_is_taken_before_duplicate_check(world, monkeypatch):
    calls = []
    real_lock, real_find = trips_module._lock_label, trips_module._find_scan
    monkeypatch.setattr(trips_module, "_lock_label", lambda *a, **k: (calls.append("lock"), real_lock(*a, **k))[1])
    monkeypatch.setattr(trips_module, "_find_scan", lambda *a, **k: (calls.append("find"), real_find(*a, **k))[1])
    assert world.scan("pickup").status_code == 200
    assert calls[:2] == ["lock", "find"]


def test_weighing_lock_is_taken_before_duplicate_check(world, monkeypatch):
    world.scan("pickup")
    calls = []
    real_lock, real_find = trips_module._lock_label, trips_module._find_weighing
    monkeypatch.setattr(trips_module, "_lock_label", lambda *a, **k: (calls.append("lock"), real_lock(*a, **k))[1])
    monkeypatch.setattr(trips_module, "_find_weighing", lambda *a, **k: (calls.append("find"), real_find(*a, **k))[1])
    assert world.weigh().status_code == 200
    assert calls[:2] == ["lock", "find"]


def _blind_first_call(monkeypatch, name):
    """Hace que el primer chequeo de duplicados no vea el evento (simula la carrera)."""
    real = getattr(trips_module, name)
    seen = {"n": 0}

    def blind(db, cid):
        seen["n"] += 1
        return None if seen["n"] == 1 else real(db, cid)

    monkeypatch.setattr(trips_module, name, blind)


def test_scan_race_on_same_event_id_returns_original_not_500(world, monkeypatch):
    first = world.scan("pickup", event="evt-race-01")
    _blind_first_call(monkeypatch, "_find_scan")
    retry = world.scan("pickup", event="evt-race-01")
    assert retry.status_code == 200
    assert retry.json()["event_id"] == first.json()["event_id"]


def test_weighing_race_on_same_event_id_returns_original_not_500(world, monkeypatch):
    world.scan("pickup")
    world.scan("pickup")
    first = world.weigh(event="evt-wrace-1")  # queda 1 cupo libre: el reintento llega al INSERT
    _blind_first_call(monkeypatch, "_find_weighing")
    retry = world.weigh(event="evt-wrace-1")
    assert retry.status_code == 200
    assert retry.json()["weighing_id"] == first.json()["weighing_id"]
    assert manifest_row(world)["weighed_count"] == 1
    assert manifest_row(world)["plant_count"] == 1  # la recepción no se duplicó


# ---------- punto 8: cierre de viaje ----------

def test_close_blocked_when_bags_pending(world):
    world.scan("pickup")
    world.scan("pickup")
    world.weigh()
    r = world.close()
    assert r.status_code == 409
    assert "no está conciliado" in r.json()["detail"]
    assert "Empresa Test (verde)" in r.json()["detail"]
    assert "retiradas 2, recibidas 1, pesadas 1" in r.json()["detail"]


def test_close_blocked_when_nothing_weighed(world):
    world.scan("pickup")
    r = world.close()
    assert r.status_code == 409 and "retiradas 1, recibidas 0, pesadas 0" in r.json()["detail"]


def test_close_ok_when_fully_reconciled(world):
    for _ in range(2):
        world.scan("pickup")
    for _ in range(2):
        assert world.weigh().status_code == 200
    r = world.close()
    assert r.status_code == 200
    assert r.json()["status"] == "closed" and r.json()["closed_at"]


def test_close_twice_is_conflict(world):
    world.scan("pickup")
    world.weigh()
    assert world.close().status_code == 200
    r = world.close()
    assert r.status_code == 409 and "ya está cerrado" in r.json()["detail"]


def test_close_force_allows_differences(world):
    world.scan("pickup")
    assert world.close().status_code == 409
    r = world.close(force=True)
    assert r.status_code == 200 and r.json()["status"] == "closed"


def test_close_empty_trip_ok(world):
    assert world.close().status_code == 200


def test_close_requires_admin_or_supervisor(world):
    assert world.close(role="collector").status_code == 403
    assert world.close(role="plant", force=True).status_code == 403


def test_close_reports_every_unbalanced_label(world):
    world.scan("pickup", color="verde")
    world.scan("pickup", color="azul")
    detail = world.close().json()["detail"]
    assert "(verde)" in detail and "(azul)" in detail


def test_closed_trip_rejects_new_events(world):
    world.close()
    assert world.scan("pickup").status_code == 409
    assert world.weigh().status_code == 409


def test_close_unknown_trip_404(client, auth):
    assert client.post("/api/v1/trips/9999/close", headers=auth["admin"]).status_code == 404
