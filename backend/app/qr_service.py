import base64
from io import BytesIO
import jwt
import qrcode
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import QrLabel


def make_qr_token(label: QrLabel) -> str:
    return jwt.encode(
        {"typ": "recycle_label", "label_id": label.id, "code": label.public_code},
        settings.qr_key,
        algorithm="HS256",
    )


def make_qr_payload(label: QrLabel) -> str:
    # El contenido físico del QR es un token firmado y permanente.
    # No depende de localhost, IP, puerto ni dominio; por eso la misma
    # etiqueta sigue siendo válida en PC, celular, demo o producción.
    return make_qr_token(label)


def qr_png_data_uri(payload: str) -> str:
    qr = qrcode.QRCode(version=None, box_size=7, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    out = BytesIO()
    image.save(out, format="PNG")
    encoded = base64.b64encode(out.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def extract_token(payload: str) -> str:
    value = payload.strip()
    if "/q/" in value:
        return value.rsplit("/q/", 1)[1].split("?", 1)[0].strip()
    return value


def resolve_label(db: Session, payload: str) -> QrLabel:
    token = extract_token(payload)
    try:
        data = jwt.decode(token, settings.qr_key, algorithms=["HS256"])
        if data.get("typ") != "recycle_label":
            raise ValueError("wrong type")
        label_id = int(data["label_id"])
        code = str(data["code"])
    except Exception:
        raise HTTPException(status_code=400, detail="QR inválido o alterado")
    label = db.scalar(select(QrLabel).where(QrLabel.id == label_id, QrLabel.public_code == code))
    if not label:
        raise HTTPException(status_code=404, detail="Etiqueta QR no encontrada")
    return label
