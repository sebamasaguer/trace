from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QrLabel, ScanEvent, ScanStage, Trip, TripStatus, User, UserRole, Weighing
from app.qr_service import resolve_label
from app.schemas import (
    ManifestOut, ManifestRow, ScanCreate, ScanResult, TripCreate, TripOut,
    WeighingCreate, WeighingResult,
)
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/trips", tags=["trips"])


def now_utc():
    return datetime.now(timezone.utc)


def _scan_count(db: Session, trip_id: int, label_id: int, stage: ScanStage) -> int:
    return int(db.scalar(select(func.count(ScanEvent.id)).where(
        ScanEvent.trip_id == trip_id,
        ScanEvent.qr_label_id == label_id,
        ScanEvent.stage == stage,
    )) or 0)


def _weighing_count(db: Session, trip_id: int, label_id: int) -> int:
    return int(db.scalar(select(func.count(Weighing.id)).where(
        Weighing.trip_id == trip_id,
        Weighing.qr_label_id == label_id,
    )) or 0)


def _scan_progress(db: Session, trip_id: int, label_id: int, stage: ScanStage) -> tuple[int, int | None, int | None]:
    if stage == ScanStage.pickup:
        registered = _scan_count(db, trip_id, label_id, ScanStage.pickup)
        return registered, None, None

    pickup_count = _scan_count(db, trip_id, label_id, ScanStage.pickup)
    plant_count = _scan_count(db, trip_id, label_id, ScanStage.plant)
    return plant_count, pickup_count, max(0, pickup_count - plant_count)


@router.get("", response_model=list[TripOut])
def list_trips(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Trip).order_by(Trip.started_at.desc()).limit(100)).all())


@router.post("", response_model=TripOut)
def create_trip(
    body: TripCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.collector, UserRole.supervisor)),
):
    stamp = now_utc().strftime("%Y%m%d-%H%M%S")
    route = f"R-{stamp}"
    suffix = 1
    while db.scalar(select(Trip.id).where(Trip.route_code == route)):
        suffix += 1
        route = f"R-{stamp}-{suffix}"
    trip = Trip(route_code=route, vehicle=body.vehicle.strip(), collector_name=body.collector_name.strip())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/scan", response_model=ScanResult)
def scan_bag(
    trip_id: int,
    body: ScanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=409, detail="El viaje está cerrado")
    if body.stage == ScanStage.pickup and user.role not in {UserRole.admin, UserRole.collector, UserRole.supervisor}:
        raise HTTPException(status_code=403, detail="Este usuario no puede registrar retiros")
    if body.stage == ScanStage.plant and user.role not in {UserRole.admin, UserRole.plant, UserRole.supervisor}:
        raise HTTPException(status_code=403, detail="Este usuario no puede registrar recepción en planta")

    duplicate = db.scalar(select(ScanEvent).where(ScanEvent.client_event_id == body.client_event_id))
    if duplicate:
        label = duplicate.label
        registered, limit, remaining = _scan_progress(db, trip_id, label.id, duplicate.stage)
        return ScanResult(
            event_id=duplicate.id,
            company_name=label.company.name,
            color=label.color,
            material_name=label.material_name,
            stage=duplicate.stage,
            scanned_at=duplicate.scanned_at,
            registered_count=registered,
            limit_count=limit,
            remaining_count=remaining,
        )

    label = resolve_label(db, body.qr_payload)

    # Bloqueo pesimista por EMPRESA+COLOR. Evita que dos celulares concurrentes
    # superen el cupo de recepción o pesaje en una carrera count -> insert.
    label = db.scalar(
        select(QrLabel).where(QrLabel.id == label.id).with_for_update()
    )
    if not label:
        raise HTTPException(status_code=404, detail="QR no encontrado")

    limit_count: int | None = None
    remaining_count: int | None = None

    if body.stage == ScanStage.plant:
        pickup_count = _scan_count(db, trip_id, label.id, ScanStage.pickup)
        plant_count = _scan_count(db, trip_id, label.id, ScanStage.plant)

        if pickup_count == 0:
            raise HTTPException(status_code=409, detail="Este QR no tiene bolsas declaradas por el recolector en este viaje")
        if plant_count >= pickup_count:
            raise HTTPException(
                status_code=409,
                detail=f"Cupo completo: ya se verificaron {plant_count} de {pickup_count} bolsas para este QR",
            )
        if trip.status == TripStatus.open:
            trip.status = TripStatus.arrived
            trip.arrived_at = now_utc()

        limit_count = pickup_count
        registered_count = plant_count + 1
        remaining_count = max(0, pickup_count - registered_count)
    else:
        registered_count = _scan_count(db, trip_id, label.id, ScanStage.pickup) + 1

    event = ScanEvent(
        trip_id=trip_id,
        qr_label_id=label.id,
        stage=body.stage,
        client_event_id=body.client_event_id,
        scanned_by=user.full_name,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return ScanResult(
        event_id=event.id,
        company_name=label.company.name,
        color=label.color,
        material_name=label.material_name,
        stage=event.stage,
        scanned_at=event.scanned_at,
        registered_count=registered_count,
        limit_count=limit_count,
        remaining_count=remaining_count,
    )


@router.post("/{trip_id}/weighings", response_model=WeighingResult)
def register_weight(
    trip_id: int,
    body: WeighingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.plant, UserRole.supervisor)),
):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=409, detail="El viaje está cerrado")

    duplicate = db.scalar(select(Weighing).where(Weighing.client_event_id == body.client_event_id))
    if duplicate:
        label = duplicate.label
        received_count = _scan_count(db, trip_id, label.id, ScanStage.plant)
        weighed_count = _weighing_count(db, trip_id, label.id)
        return WeighingResult(
            weighing_id=duplicate.id,
            company_name=label.company.name,
            color=label.color,
            material_name=label.material_name,
            weight_kg=duplicate.weight_kg,
            weighed_at=duplicate.weighed_at,
            weighed_count=weighed_count,
            limit_count=received_count,
            remaining_count=max(0, received_count - weighed_count),
        )

    label = resolve_label(db, body.qr_payload)
    label = db.scalar(
        select(QrLabel).where(QrLabel.id == label.id).with_for_update()
    )
    if not label:
        raise HTTPException(status_code=404, detail="QR no encontrado")

    pickup_count = _scan_count(db, trip_id, label.id, ScanStage.pickup)
    received_count = _scan_count(db, trip_id, label.id, ScanStage.plant)
    weighed_count = _weighing_count(db, trip_id, label.id)

    if pickup_count == 0:
        raise HTTPException(status_code=409, detail="Este QR no fue recolectado en este viaje")
    if received_count == 0:
        raise HTTPException(status_code=409, detail="Primero debe verificarse esta bolsa en recepción de planta")

    # Límite efectivo: nunca más que lo recolectado y, además, exige recepción previa.
    effective_limit = min(pickup_count, received_count)
    if weighed_count >= effective_limit:
        raise HTTPException(
            status_code=409,
            detail=f"Cupo completo: ya se pesaron {weighed_count} de {effective_limit} bolsas habilitadas para este QR",
        )

    weighing = Weighing(
        trip_id=trip_id,
        qr_label_id=label.id,
        weight_kg=body.weight_kg,
        client_event_id=body.client_event_id,
        weighed_by=user.full_name,
    )
    db.add(weighing)
    db.commit()
    db.refresh(weighing)

    new_weighed_count = weighed_count + 1
    return WeighingResult(
        weighing_id=weighing.id,
        company_name=label.company.name,
        color=label.color,
        material_name=label.material_name,
        weight_kg=weighing.weight_kg,
        weighed_at=weighing.weighed_at,
        weighed_count=new_weighed_count,
        limit_count=effective_limit,
        remaining_count=max(0, effective_limit - new_weighed_count),
    )


@router.get("/{trip_id}/manifest", response_model=ManifestOut)
def manifest(trip_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    data: dict[int, dict] = {}
    labels = db.scalars(select(QrLabel)).all()
    label_map = {label.id: label for label in labels}

    scans = db.scalars(select(ScanEvent).where(ScanEvent.trip_id == trip_id)).all()
    for event in scans:
        label = label_map[event.qr_label_id]
        row = data.setdefault(label.id, {
            "label": label, "pickup": 0, "plant": 0, "weighed": 0, "kg": Decimal("0")
        })
        if event.stage == ScanStage.pickup:
            row["pickup"] += 1
        else:
            row["plant"] += 1

    weighings = db.scalars(select(Weighing).where(Weighing.trip_id == trip_id)).all()
    for w in weighings:
        label = label_map[w.qr_label_id]
        row = data.setdefault(label.id, {
            "label": label, "pickup": 0, "plant": 0, "weighed": 0, "kg": Decimal("0")
        })
        row["weighed"] += 1
        row["kg"] += Decimal(w.weight_kg)

    rows: list[ManifestRow] = []
    for item in sorted(data.values(), key=lambda x: (x["label"].company.name, x["label"].color.value)):
        label = item["label"]
        rows.append(ManifestRow(
            company_id=label.company.id,
            company_name=label.company.name,
            color=label.color,
            material_name=label.material_name,
            pickup_count=item["pickup"],
            plant_count=item["plant"],
            difference=item["plant"] - item["pickup"],
            weighed_count=item["weighed"],
            total_kg=item["kg"],
        ))

    return ManifestOut(
        trip=trip,
        rows=rows,
        pickup_total=sum(r.pickup_count for r in rows),
        plant_total=sum(r.plant_count for r in rows),
        difference_total=sum(r.plant_count - r.pickup_count for r in rows),
        weighed_total=sum(r.weighed_count for r in rows),
        kg_total=sum((r.total_kg for r in rows), Decimal("0")),
    )


@router.post("/{trip_id}/close", response_model=TripOut)
def close_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    trip.status = TripStatus.closed
    trip.closed_at = now_utc()
    db.commit()
    db.refresh(trip)
    return trip
