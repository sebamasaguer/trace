from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Company, QrLabel, User, UserRole, WasteColor
from app.security import hash_password

MATERIALS = {
    WasteColor.amarillo: "Plásticos",
    WasteColor.verde: "Vidrio",
    WasteColor.azul: "Papel / Cartón",
}


def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        users = [
            ("admin", "Administrador Demo", UserRole.admin, "Admin123!"),
            ("recolector", "Juan Recolector", UserRole.collector, "Recolector123!"),
            ("planta", "Operador Planta", UserRole.plant, "Planta123!"),
        ]
        for username, full_name, role, password in users:
            if not db.scalar(select(User).where(User.username == username)):
                db.add(User(username=username, full_name=full_name, role=role, password_hash=hash_password(password)))
        db.flush()

        if not db.scalar(select(Company).limit(1)):
            company = Company(name="Empresa Demo S.A.", tax_id="30-00000000-0", site_name="Casa Central")
            db.add(company)
            db.flush()
            for color, material in MATERIALS.items():
                db.add(QrLabel(
                    company_id=company.id,
                    color=color,
                    material_name=material,
                    public_code=f"DEMO-{color.value.upper()}",
                ))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
