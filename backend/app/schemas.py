from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models import ScanStage, TripStatus, UserRole, WasteColor


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    full_name: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    model_config = ConfigDict(from_attributes=True)


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    tax_id: str | None = None
    site_name: str | None = None


class CompanyOut(BaseModel):
    id: int
    name: str
    tax_id: str | None
    site_name: str | None
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LabelOut(BaseModel):
    id: int
    color: WasteColor
    material_name: str
    public_code: str
    qr_payload: str
    qr_data_uri: str


class LabelVerifyOut(BaseModel):
    company_id: int
    company_name: str
    color: WasteColor
    material_name: str
    public_code: str


class TripCreate(BaseModel):
    vehicle: str = Field(min_length=2, max_length=80)
    collector_name: str = Field(min_length=2, max_length=160)


class TripOut(BaseModel):
    id: int
    route_code: str
    vehicle: str
    collector_name: str
    status: TripStatus
    started_at: datetime
    arrived_at: datetime | None
    closed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class ScanCreate(BaseModel):
    qr_payload: str
    stage: ScanStage
    client_event_id: str = Field(min_length=8, max_length=80)


class ScanResult(BaseModel):
    event_id: int
    company_name: str
    color: WasteColor
    material_name: str
    stage: ScanStage
    scanned_at: datetime
    registered_count: int
    limit_count: int | None = None
    remaining_count: int | None = None


class WeighingCreate(BaseModel):
    qr_payload: str
    company_id: int = Field(gt=0, description="Empresa seleccionada para esta sesión de pesaje")
    weight_kg: Decimal = Field(gt=0, le=10000)
    client_event_id: str = Field(min_length=8, max_length=80)


class WeighingResult(BaseModel):
    weighing_id: int
    company_name: str
    color: WasteColor
    material_name: str
    weight_kg: Decimal
    weighed_at: datetime
    weighed_count: int
    limit_count: int
    remaining_count: int


class ManifestRow(BaseModel):
    company_id: int
    company_name: str
    color: WasteColor
    material_name: str
    pickup_count: int
    plant_count: int
    difference: int
    weighed_count: int
    total_kg: Decimal


class ManifestOut(BaseModel):
    trip: TripOut
    rows: list[ManifestRow]
    pickup_total: int
    plant_total: int
    difference_total: int
    weighed_total: int
    kg_total: Decimal


class DashboardOut(BaseModel):
    active_companies: int
    open_trips: int
    bags_collected_today: int
    bags_received_today: int
    kg_today: Decimal
    kg_month: Decimal
    mismatch_count: int
