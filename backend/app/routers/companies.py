import secrets
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, QrLabel, User, UserRole, WasteColor
from app.qr_service import make_qr_payload, qr_png_data_uri, resolve_label
from app.schemas import CompanyCreate, CompanyOut, LabelOut, LabelVerifyOut
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/companies", tags=["companies"])
MATERIALS = {
    WasteColor.amarillo: "Plásticos",
    WasteColor.verde: "Vidrio",
    WasteColor.azul: "Papel / Cartón",
}


@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Company).order_by(Company.name)).all())


@router.post("", response_model=CompanyOut)
def create_company(
    body: CompanyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
):
    company = Company(name=body.name.strip(), tax_id=body.tax_id, site_name=body.site_name)
    db.add(company)
    db.flush()
    for color, material in MATERIALS.items():
        db.add(QrLabel(
            company_id=company.id,
            color=color,
            material_name=material,
            public_code=f"C{company.id}-{color.value[:3].upper()}-{secrets.token_hex(4).upper()}",
        ))
    db.commit()
    db.refresh(company)
    return company


@router.get("/verify/label", response_model=LabelVerifyOut)
def verify_label(payload: str = Query(...), db: Session = Depends(get_db)):
    label = resolve_label(db, payload)
    return LabelVerifyOut(
        company_id=label.company.id,
        company_name=label.company.name,
        color=label.color,
        material_name=label.material_name,
        public_code=label.public_code,
    )


@router.get("/{company_id}/labels", response_model=list[LabelOut])
def company_labels(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    labels = db.scalars(select(QrLabel).where(QrLabel.company_id == company_id).order_by(QrLabel.color)).all()
    return [
        LabelOut(
            id=label.id,
            color=label.color,
            material_name=label.material_name,
            public_code=label.public_code,
            qr_payload=make_qr_payload(label),
            qr_data_uri=qr_png_data_uri(make_qr_payload(label)),
        )
        for label in labels
    ]
