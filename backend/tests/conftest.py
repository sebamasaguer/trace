import os

# Debe fijarse antes de importar la app: Settings se construye al importar.
os.environ["SECRET_KEY"] = "test-session-secret-0123456789abcdef"
os.environ["QR_SECRET_KEY"] = "test-qr-secret-fedcba9876543210"
os.environ["DATABASE_URL"] = "sqlite://"

import itertools

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.security import hash_password

USERS = {
    "admin": ("Admin Test", UserRole.admin, "Admin123!"),
    "collector": ("Recolector Test", UserRole.collector, "Recolector123!"),
    "plant": ("Planta Test", UserRole.plant, "Planta123!"),
}

# argon2 es lento a propósito: se hashea una sola vez para toda la sesión.
_HASHES = {name: hash_password(pw) for name, (_, _, pw) in USERS.items()}


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with factory() as db:
        for username, (full_name, role, _) in USERS.items():
            db.add(User(username=username, full_name=full_name, role=role, password_hash=_HASHES[username]))
        db.commit()
    yield factory
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def auth(client):
    """Cabeceras Authorization por rol: auth['admin'], auth['collector'], auth['plant']."""
    headers = {}
    for username, (_, _, password) in USERS.items():
        res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert res.status_code == 200, res.text
        headers[username] = {"Authorization": f"Bearer {res.json()['access_token']}"}
    return headers


@pytest.fixture()
def world(client, auth):
    """Empresa con sus 3 QR y un viaje abierto, más helpers de API."""
    company = client.post("/api/v1/companies", json={"name": "Empresa Test"}, headers=auth["admin"])
    assert company.status_code == 200, company.text
    labels = client.get(f"/api/v1/companies/{company.json()['id']}/labels", headers=auth["admin"]).json()
    qr = {l["color"]: l["qr_payload"] for l in labels}
    trip = client.post(
        "/api/v1/trips", json={"vehicle": "AB123CD", "collector_name": "Juan"}, headers=auth["collector"]
    )
    assert trip.status_code == 200, trip.text
    counter = itertools.count(1)

    class World:
        pass

    w = World()
    w.client, w.auth, w.qr, w.trip_id = client, auth, qr, trip.json()["id"]
    w.company_id = company.json()["id"]

    def event_id():
        return f"evt-{next(counter):06d}"

    def scan(stage, color="verde", role=None, event=None, trip_id=None):
        role = role or ("collector" if stage == "pickup" else "plant")
        return client.post(
            f"/api/v1/trips/{trip_id or w.trip_id}/scan",
            json={"qr_payload": qr[color], "stage": stage, "client_event_id": event or event_id()},
            headers=auth[role],
        )

    def weigh(color="verde", kg="10.5", event=None):
        return client.post(
            f"/api/v1/trips/{w.trip_id}/weighings",
            json={"qr_payload": qr[color], "weight_kg": kg, "client_event_id": event or event_id()},
            headers=auth["plant"],
        )

    def close(role="admin", force=False):
        return client.post(
            f"/api/v1/trips/{w.trip_id}/close", params={"force": str(force).lower()}, headers=auth[role]
        )

    w.scan, w.weigh, w.close, w.event_id = scan, weigh, close, event_id
    return w
