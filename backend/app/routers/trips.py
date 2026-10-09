from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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


def _find_scan(db: Session, client_event_id: str) -> ScanEvent | None:
    return db.scalar(select(ScanEvent).where(ScanEvent.client_event_id == client_event_id))


def _find_weighing(db: Session, client_event_id: str) -> Weighing | None:
    return db.scalar(select(Weighing).where(Weighing.client_event_id == client_event_id))


def _scan_result_from_event(db: Session, event: ScanEvent) -> ScanResult:
    label = event.label
    registered, limit, remaining = _scan_progress(db, event.trip_id, label.id, event.stage)
    return ScanResult(
        event_id=event.id,
        company_name=label.company.name,
        color=label.color,
        material_name=label.material_name,
        stage=event.stage,
        scanned_at=event.scanned_at,
        registered_count=registered,
        limit_count=limit,
        remaining_count=remaining,
    )


def _weighing_result_from_existing(db: Session, weighing: Weighing) -> WeighingResult:
    label = weighing.label
    received_count = _scan_count(db, weighing.trip_id, label.id, ScanStage.plant)
    weighed_count = _weighing_count(db, weighing.trip_id, label.id)
    return WeighingResult(
        weighing_id=weighing.id,
        company_name=label.company.name,
        color=label.color,
        material_name=label.material_name,
        weight_kg=weighing.weight_kg,
        weighed_at=weighing.weighed_at,
        weighed_count=weighed_count,
        limit_count=received_count,
        remaining_count=max(0, received_count - weighed_count),
    )


def _lock_label(db: Session, payload: str) -> QrLabel:
    """Resuelve el QR y toma un bloqueo pesimista por EMPRESA+COLOR.

    Debe llamarse ANTES de consultar duplicados y cupos: así dos peticiones
    concurrentes (incluido un reintento con el mismo client_event_id) quedan
    serializadas y la segunda ve el evento ya confirmado por la primera.
    """
    label = resolve_label(db, payload)
    locked = db.scalar(select(QrLabel).where(QrLabel.id == label.id).with_for_update())
    if not locked:
        raise HTTPException(status_code=404, detail="QR no encontrado")
    return locked


def _reconciliation_issues(db: Session, trip_id: int) -> list[str]:
    """Etiquetas del viaje cuyo retiro, recepción y pesaje no coinciden."""
    counts: dict[int, dict[str, int]] = {}
    scan_rows = db.execute(
        select(ScanEvent.qr_label_id, ScanEvent.stage, func.count(ScanEvent.id))
        .where(ScanEvent.trip_id == trip_id)
        .group_by(ScanEvent.qr_label_id, ScanEvent.stage)
    ).all()
    for label_id, stage, total in scan_rows:
        counts.setdefault(label_id, {"pickup": 0, "plant": 0, "weighed": 0})[stage.value] = total
    weigh_rows = db.execute(
        select(Weighing.qr_label_id, func.count(Weighing.id))
        .where(Weighing.trip_id == trip_id)
        .group_by(Weighing.qr_label_id)
    ).all()
    for label_id, total in weigh_rows:
        counts.setdefault(label_id, {"pickup": 0, "plant": 0, "weighed": 0})["weighed"] = total

    bad = {lid: c for lid, c in counts.items() if not (c["pickup"] == c["plant"] == c["weighed"])}
    if not bad:
        return []
    labels = db.scalars(select(QrLabel).where(QrLabel.id.in_(bad))).all()
    issues = [
        f"{l.company.name} ({l.color.value}): retiradas {bad[l.id]['pickup']}, "
        f"recibidas {bad[l.id]['plant']}, pesadas {bad[l.id]['weighed']}"
        for l in sorted(labels, key=lambda l: (l.company.name, l.color.value))
    ]
    return issues


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

    label = _lock_label(db, body.qr_payload)
    db.refresh(trip)  # el estado pudo cambiar mientras se esperaba el bloqueo

    # Con el bloqueo tomado, el chequeo de idempotencia ya no compite con otra petición.
    duplicate = _find_scan(db, body.client_event_id)
    if duplicate:
        return _scan_result_from_event(db, duplicate)

    # Una vez que la planta empezó a recibir (arrived) el manifiesto de retiro queda congelado.
    if body.stage == ScanStage.pickup and trip.status != TripStatus.open:
        raise HTTPException(
            status_code=409,
            detail="El viaje ya está en recepción de planta: no se pueden registrar más retiros",
        )

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
    try:
        db.commit()
    except IntegrityError:
        # Red de seguridad: otra petición con el mismo client_event_id ganó la carrera.
        db.rollback()
        existing = _find_scan(db, body.client_event_id)
        if existing:
            return _scan_result_from_event(db, existing)
        raise
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

    label = _lock_label(db, body.qr_payload)

    duplicate = _find_weighing(db, body.client_event_id)
    if duplicate:
        return _weighing_result_from_existing(db, duplicate)

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
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _find_weighing(db, body.client_event_id)
        if existing:
            return _weighing_result_from_existing(db, existing)
        raise
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
    force: bool = Query(False, description="Cerrar aunque haya diferencias (bolsas faltantes o sin pesar)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update())
    if not trip:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    if trip.status == TripStatus.closed:
        raise HTTPException(status_code=409, detail="El viaje ya está cerrado")
    if not force:
        issues = _reconciliation_issues(db, trip_id)
        if issues:
            shown = "; ".join(issues[:5])
            extra = f" (y {len(issues) - 5} más)" if len(issues) > 5 else ""
            raise HTTPException(
                status_code=409,
                detail=f"El viaje no está conciliado: {shown}{extra}. Use force=true para cerrar con diferencias.",
            )
    trip.status = TripStatus.closed
    trip.closed_at = now_utc()
    db.commit()
    db.refresh(trip)
    return trip
