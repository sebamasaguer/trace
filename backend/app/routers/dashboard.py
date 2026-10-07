from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, ScanEvent, ScanStage, Trip, TripStatus, User, Weighing
from app.schemas import DashboardOut
from app.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    active_companies = db.scalar(select(func.count(Company.id)).where(Company.is_active.is_(True))) or 0
    open_trips = db.scalar(select(func.count(Trip.id)).where(Trip.status != TripStatus.closed)) or 0
    bags_collected_today = db.scalar(select(func.count(ScanEvent.id)).where(
        ScanEvent.stage == ScanStage.pickup, ScanEvent.scanned_at >= day_start
    )) or 0
    bags_received_today = db.scalar(select(func.count(ScanEvent.id)).where(
        ScanEvent.stage == ScanStage.plant, ScanEvent.scanned_at >= day_start
    )) or 0
    kg_today = db.scalar(select(func.coalesce(func.sum(Weighing.weight_kg), 0)).where(Weighing.weighed_at >= day_start)) or 0
    kg_month = db.scalar(select(func.coalesce(func.sum(Weighing.weight_kg), 0)).where(Weighing.weighed_at >= month_start)) or 0

    pickup_by_trip = dict(db.execute(select(ScanEvent.trip_id, func.count(ScanEvent.id)).where(
        ScanEvent.stage == ScanStage.pickup
    ).group_by(ScanEvent.trip_id)).all())
    plant_by_trip = dict(db.execute(select(ScanEvent.trip_id, func.count(ScanEvent.id)).where(
        ScanEvent.stage == ScanStage.plant
    ).group_by(ScanEvent.trip_id)).all())
    mismatch_count = sum(1 for trip_id, count in pickup_by_trip.items() if plant_by_trip.get(trip_id, 0) != count)

    return DashboardOut(
        active_companies=active_companies,
        open_trips=open_trips,
        bags_collected_today=bags_collected_today,
        bags_received_today=bags_received_today,
        kg_today=Decimal(kg_today),
        kg_month=Decimal(kg_month),
        mismatch_count=mismatch_count,
    )
