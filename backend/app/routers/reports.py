"""Reportería de recolección y pesaje por empresa, con fechas de Salta (UTC-3).

Las métricas usan la fecha del evento correspondiente, por lo que un retiro y
su pesaje pueden pertenecer a períodos diferentes. No se inventan emparejamientos
por bolsa: un QR identifica empresa y color, no cada bolsa física.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, QrLabel, ScanEvent, ScanStage, User, WasteColor, Weighing
from app.security import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])
LOCAL_TZ = timezone(timedelta(hours=-3))
UTC = timezone.utc


class Period(str, Enum):
    day = "day"
    week = "week"
    month = "month"
    year = "year"


def _range_for(period: Period, reference: date) -> tuple[date, date]:
    if period == Period.day:
        start = reference
        end = reference + timedelta(days=1)
    elif period == Period.week:
        start = reference - timedelta(days=reference.weekday())
        end = start + timedelta(days=7)
    elif period == Period.month:
        start = reference.replace(day=1)
        end = start.replace(year=start.year+1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    else:
        start, end = date(reference.year, 1, 1), date(reference.year + 1, 1, 1)
    return start, end


def _date_bucket(column, db: Session):
    # En PostgreSQL, convertir explícitamente el timestamp a hora local antes
    # de agrupar. En SQLite (tests) emplear el modificador equivalente.
    if db.bind and db.bind.dialect.name == "sqlite":
        return func.date(column, "-3 hours")
    return func.date(func.timezone("America/Argentina/Salta", column))


def _format_group(day: date, period: Period) -> str:
    if period == Period.year:
        return f"{day.year}-{day.month:02d}"
    return day.isoformat()


@router.get("/company/{company_id}")
def company_report(
    company_id: int,
    period: Period = Query(Period.month),
    reference_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    reference = reference_date or datetime.now(LOCAL_TZ).date()
    start, end = _range_for(period, reference)
    utc_start = datetime.combine(start, time.min, LOCAL_TZ).astimezone(UTC)
    utc_end = datetime.combine(end, time.min, LOCAL_TZ).astimezone(UTC)

    # Grupo por empresa, color y fecha. El cómputo se hace en la base de datos
    # (no se cargan todos los eventos en memoria).
    pickup_day = _date_bucket(ScanEvent.scanned_at, db)
    weight_day = _date_bucket(Weighing.weighed_at, db)
    pickups = db.execute(
        select(QrLabel.color, pickup_day.label("d"), func.count(ScanEvent.id))
        .join(QrLabel, QrLabel.id == ScanEvent.qr_label_id)
        .where(QrLabel.company_id == company_id, ScanEvent.stage == ScanStage.pickup,
               ScanEvent.scanned_at >= utc_start, ScanEvent.scanned_at < utc_end)
        .group_by(QrLabel.color, pickup_day)
    ).all()
    weights = db.execute(
        select(QrLabel.color, weight_day.label("d"), func.count(Weighing.id),
               func.coalesce(func.sum(Weighing.weight_kg), 0))
        .join(QrLabel, QrLabel.id == Weighing.qr_label_id)
        .where(QrLabel.company_id == company_id,
               Weighing.weighed_at >= utc_start, Weighing.weighed_at < utc_end)
        .group_by(QrLabel.color, weight_day)
    ).all()

    per_color = {color.value: {"color": color.value, "material_name": material,
                               "collected": 0, "weighed": 0, "kg": Decimal("0")}
                 for color, material in [(WasteColor.amarillo, "Plásticos"),
                                         (WasteColor.verde, "Vidrio"),
                                         (WasteColor.azul, "Papel / Cartón")]}
    buckets = defaultdict(lambda: {"collected": 0, "weighed": 0, "kg": Decimal("0")})

    for color, raw_day, count in pickups:
        day = date.fromisoformat(str(raw_day)[:10])
        k = _format_group(day, period)
        per_color[color.value]["collected"] += int(count)
        buckets[k]["collected"] += int(count)
    for color, raw_day, count, kg in weights:
        day = date.fromisoformat(str(raw_day)[:10])
        k = _format_group(day, period)
        per_color[color.value]["weighed"] += int(count)
        per_color[color.value]["kg"] += Decimal(str(kg)).quantize(Decimal("0.001"))
        buckets[k]["weighed"] += int(count)
        buckets[k]["kg"] += Decimal(str(kg)).quantize(Decimal("0.001"))

    # Completar eje temporal incluso para días/meses sin movimientos.
    cursor = start
    step = "month" if period == Period.year else "day"
    while cursor < end:
        _ = buckets[_format_group(cursor, period)]
        if step == "month":
            cursor = cursor.replace(year=cursor.year+1, month=1) if cursor.month == 12 else cursor.replace(month=cursor.month+1)
        else:
            cursor += timedelta(days=1)

    colors = [{**row, "kg": str(row["kg"])} for row in per_color.values()]
    timeline = [{"period": k, "collected": v["collected"], "weighed": v["weighed"], "kg": str(v["kg"])}
                for k, v in sorted(buckets.items())]
    return {
        "company_id": company.id,
        "company_name": company.name,
        "period": period.value,
        "reference_date": reference,
        "start_date": start,
        "end_date_exclusive": end,
        "timezone": "America/Argentina/Salta",
        "collected_total": sum(row["collected"] for row in colors),
        "weighed_total": sum(row["weighed"] for row in colors),
        "kg_total": str(sum((Decimal(row["kg"]) for row in colors), Decimal("0"))),
        "colors": colors,
        "timeline": timeline,
    }
