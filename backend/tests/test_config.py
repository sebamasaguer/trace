import jwt
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models import QrLabel
from app.qr_service import make_qr_token, resolve_label

GOOD = "a-perfectly-fine-secret-key-123"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # conftest fija estas variables para la app; aquí se prueba Settings en aislamiento.
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("QR_SECRET_KEY", raising=False)


def make(**kw):
    return Settings(_env_file=None, **kw)


def test_rejects_default_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make()


@pytest.mark.parametrize("value", ["change-this-secret-in-production", "change-me-in-production", "short"])
def test_rejects_example_or_short_secret(value):
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make(secret_key=value)


def test_rejects_qr_key_equal_to_session_key():
    with pytest.raises(ValidationError, match="distinto"):
        make(secret_key=GOOD, qr_secret_key=GOOD)


def test_rejects_weak_qr_key():
    with pytest.raises(ValidationError, match="QR_SECRET_KEY"):
        make(secret_key=GOOD, qr_secret_key="change-me-in-production")


def test_empty_qr_key_falls_back_to_derived():
    s = make(secret_key=GOOD, qr_secret_key="")
    assert s.qr_key and s.qr_key != GOOD


def test_derived_qr_key_is_stable_and_differs_from_session_key():
    a, b = make(secret_key=GOOD), make(secret_key=GOOD)
    assert a.qr_key == b.qr_key != GOOD
    assert make(secret_key=GOOD + "x").qr_key != a.qr_key


def test_explicit_qr_key_is_used():
    s = make(secret_key=GOOD, qr_secret_key="another-long-enough-qr-secret")
    assert s.qr_key == "another-long-enough-qr-secret"


def _label(session_factory):
    from app.models import Company
    from app.models import WasteColor

    with session_factory() as db:
        c = Company(name="X")
        db.add(c)
        db.flush()
        l = QrLabel(company_id=c.id, color=WasteColor.verde, material_name="Vidrio", public_code="C1-VER-AAAA")
        db.add(l)
        db.commit()
        return l.id, l.public_code


def test_qr_token_signed_with_session_key_is_rejected(session_factory):
    from app.config import settings
    from fastapi import HTTPException

    label_id, code = _label(session_factory)
    forged = jwt.encode(
        {"typ": "recycle_label", "label_id": label_id, "code": code}, settings.secret_key, algorithm="HS256"
    )
    with session_factory() as db, pytest.raises(HTTPException) as exc:
        resolve_label(db, forged)
    assert exc.value.status_code == 400


def test_valid_qr_token_resolves_and_is_not_a_session_token(session_factory, client):
    label_id, code = _label(session_factory)
    with session_factory() as db:
        label = db.get(QrLabel, label_id)
        token = make_qr_token(label)
        assert resolve_label(db, token).id == label_id
    # Un token de QR no sirve como sesión.
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
