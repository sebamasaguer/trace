"""Golden funcional v0.1.7 con SQLite efímero. No utiliza datos del usuario."""
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

DB = Path(__file__).resolve().parent / "_test_v017.sqlite3"
if DB.exists():
    DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Company, QrLabel, ScanEvent, ScanStage, Trip, User, UserRole, WasteColor, Weighing
from app.qr_service import make_qr_payload
from app.security import hash_password

Base.metadata.create_all(engine)
with SessionLocal() as db:
    db.add_all([
        User(username="admin_rt017", full_name="Admin Test", role=UserRole.admin, password_hash=hash_password("Valid123!")),
        User(username="planta_rt017", full_name="Operario Test", role=UserRole.plant, password_hash=hash_password("Valid123!")),
    ])
    company = Company(name="Empresa Golden", site_name="Sede Test")
    db.add(company)
    db.flush()
    for c in WasteColor:
        db.add(QrLabel(company_id=company.id,color=c,material_name=c.value,public_code="TEST-"+c.value.upper()))
    db.commit()

client = TestClient(app)

def token(user):
    res = client.post("/api/v1/auth/login", json={"username":user, "password":"Valid123!"})
    assert res.status_code == 200, res.text
    return {"Authorization":"Bearer "+res.json()["access_token"]}

admin = token("admin_rt017")
plant = token("planta_rt017")
with SessionLocal() as db:
    company = db.scalar(select(Company).where(Company.name=="Empresa Golden"))
    company_id=company.id
    qr = {l.color.value:make_qr_payload(l) for l in db.scalars(select(QrLabel).where(QrLabel.company_id==company_id))}


def post_pickup(trip, color):
    r=client.post(f"/api/v1/trips/{trip}/scan",json={"qr_payload":qr[color],"stage":"pickup","client_event_id":str(uuid4())},headers=admin)
    assert r.status_code == 200, r.text


def post_weight(trip, color, value, uuid=None):
    return client.post(f"/api/v1/trips/{trip}/weighings",json={"qr_payload":qr[color],"company_id":company_id,"weight_kg":value,"client_event_id":uuid or str(uuid4())},headers=plant)


def test_recepcion_integrada_y_reporte():
    trip_resp=client.post('/api/v1/trips',json={"vehicle":"TEST-017","collector_name":"Golden"},headers=admin)
    assert trip_resp.status_code==200, trip_resp.text
    tid=trip_resp.json()['id']
    for c,n in [('amarillo',4),('verde',3),('azul',2)]:
        for _ in range(n): post_pickup(tid,c)
    r=client.post(f"/api/v1/trips/{tid}/scan",json={"qr_payload":qr['amarillo'],"stage":"plant","client_event_id":str(uuid4())},headers=plant)
    assert r.status_code==409, r.text
    expected_kg=Decimal('0')
    for c,n in [('amarillo',4),('verde',3),('azul',2)]:
        for i in range(n):
            weight=str(Decimal('1.250')+Decimal(i)/100)
            expected_kg+=Decimal(weight)
            uuid=str(uuid4())
            r=post_weight(tid,c,weight,uuid)
            assert r.status_code==200, r.text
            assert r.json()['weighed_count']==i+1
            same=post_weight(tid,c,weight,uuid)
            assert same.status_code==200
            assert same.json()['weighing_id']==r.json()['weighing_id']
        excess=post_weight(tid,c,"3.100")
        assert excess.status_code==409
    manifest=client.get(f"/api/v1/trips/{tid}/manifest",headers=admin).json()
    assert manifest['pickup_total']==9
    assert manifest['plant_total']==9
    assert manifest['weighed_total']==9
    assert Decimal(manifest['kg_total'])==expected_kg
    assert manifest['difference_total']==0
    with SessionLocal() as db:
        assert len(list(db.scalars(select(Weighing).where(Weighing.trip_id==tid))))==9
        assert len(list(db.scalars(select(ScanEvent).where(ScanEvent.trip_id==tid, ScanEvent.stage==ScanStage.plant))))==9
        sample=db.scalar(select(Weighing).where(Weighing.trip_id==tid))
        assert sample is not None
        # Tomamos una fecha fija a horario local de Salta para validar filtros.
        dt=datetime(2026,10,7,15,0,tzinfo=timezone.utc)
        for scan in db.scalars(select(ScanEvent).where(ScanEvent.trip_id==tid)):
            scan.scanned_at=dt
        for w in db.scalars(select(Weighing).where(Weighing.trip_id==tid)):
            w.weighed_at=dt
        db.commit()
    for period in ('day','week','month','year'):
        rep=client.get(f'/api/v1/reports/company/{company_id}',params={'period':period,'reference_date':'2026-10-07'},headers=admin)
        assert rep.status_code==200, rep.text
        d=rep.json()
        assert d['collected_total']==9
        assert d['weighed_total']==9
        assert Decimal(d['kg_total'])==expected_kg
        assert [r['weighed'] for r in d['colors']]==[4,3,2]
        assert sum(r['collected'] for r in d['timeline'])==9
        assert sum(r['weighed'] for r in d['timeline'])==9
    day=client.get(f'/api/v1/reports/company/{company_id}',params={'period':'day','reference_date':'2026-10-08'},headers=admin).json()
    assert day['collected_total']==0 and day['kg_total']=='0'
    err=client.get(f'/api/v1/reports/company/{company_id}',params={'period':'decade'},headers=admin)
    assert err.status_code==422
    no=client.get('/api/v1/reports/company/999999',headers=admin)
    assert no.status_code==404


def test_historico_con_recepcion_separada_pendiente_de_pesar():
    r=client.post('/api/v1/trips',json={"vehicle":"TEST-OLD","collector_name":"Golden"},headers=admin)
    tid=r.json()['id']
    post_pickup(tid,'verde')
    with SessionLocal() as db:
        label=db.scalar(select(QrLabel).where(QrLabel.public_code=='TEST-VERDE'))
        db.add(ScanEvent(trip_id=tid,qr_label_id=label.id,stage=ScanStage.plant,client_event_id='legacy-'+str(uuid4()),scanned_by="Histórico"))
        db.commit()
    success=post_weight(tid,'verde','2.800')
    assert success.status_code==200,success.text
    m=client.get(f'/api/v1/trips/{tid}/manifest',headers=admin).json()
    assert (m['pickup_total'],m['plant_total'],m['weighed_total'])==(1,1,1)


def test_limite_por_viaje_y_corte_horario_salta():
    # Otro viaje de la misma empresa no hereda las cantidades de los anteriores.
    resp=client.post('/api/v1/trips',json={"vehicle":"TEST-ISO","collector_name":"Golden"},headers=admin)
    tid=resp.json()['id']
    post_pickup(tid, 'amarillo')
    r=post_weight(tid, 'amarillo', '1.300')
    assert r.status_code==200, r.text
    assert post_weight(tid, 'amarillo', '1.300').status_code==409
    with SessionLocal() as db:
        for event in db.scalars(select(ScanEvent).where(ScanEvent.trip_id==tid)):
            event.scanned_at=datetime(2026,10,7,2,0,tzinfo=timezone.utc)  # 06-oct 23:00 Salta
        for w in db.scalars(select(Weighing).where(Weighing.trip_id==tid)):
            w.weighed_at=datetime(2026,10,7,2,0,tzinfo=timezone.utc)
        db.commit()
    six=client.get(f'/api/v1/reports/company/{company_id}',params={'period':'day','reference_date':'2026-10-06'},headers=admin).json()
    seven=client.get(f'/api/v1/reports/company/{company_id}',params={'period':'day','reference_date':'2026-10-07'},headers=admin).json()
    assert six['weighed_total']==1 and six['collected_total']==1
    assert seven['weighed_total']==9 and seven['collected_total']==9


def test_empresa_ajena_en_el_mismo_viaje_y_contexto_obligatorio():
    """Dos clientes en el camión: QR de empresa B nunca entra al pesaje de A."""
    with SessionLocal() as db:
        other = Company(name="Empresa Intrusa", site_name="Sede B")
        db.add(other)
        db.flush()
        other_id = other.id
        label = QrLabel(company_id=other_id, color=WasteColor.amarillo,
                        material_name="Plásticos", public_code="TEST-B-AMARILLO")
        db.add(label)
        db.flush()
        other_qr = make_qr_payload(label)
        db.commit()
    trip = client.post('/api/v1/trips', json={"vehicle":"CAMION-MIXTO","collector_name":"Golden"},headers=admin).json()['id']
    post_pickup(trip,'amarillo')
    other_pickup = client.post(f'/api/v1/trips/{trip}/scan',json={"qr_payload":other_qr,"stage":"pickup","client_event_id":str(uuid4())},headers=admin)
    assert other_pickup.status_code == 200, other_pickup.text
    mismatch_event = str(uuid4())
    def send(qr_payload, declared_id, event_id, weight="4.500"):
        return client.post(f'/api/v1/trips/{trip}/weighings',json={"qr_payload":qr_payload,"company_id":declared_id,"weight_kg":weight,"client_event_id":event_id},headers=plant)
    invalid=send(other_qr,company_id,mismatch_event)
    assert invalid.status_code == 409, invalid.text
    assert 'EMPRESA INCORRECTA' in invalid.json()['detail']
    assert 'Empresa Intrusa' in invalid.json()['detail']
    manifest=client.get(f'/api/v1/trips/{trip}/manifest',headers=admin).json()
    assert manifest['pickup_total']==2
    assert manifest['plant_total']==0 and manifest['weighed_total']==0
    missing=client.post(f'/api/v1/trips/{trip}/weighings',json={"qr_payload":other_qr,"weight_kg":"3","client_event_id":str(uuid4())},headers=plant)
    assert missing.status_code == 422, missing.text
    good=send(qr['amarillo'], company_id, str(uuid4()))
    assert good.status_code==200,good.text
    other_good=send(other_qr,other_id,mismatch_event)
    assert other_good.status_code==200, other_good.text
    # Reutilizar el ID desde otra bolsa o con otro peso jamás cambia el registro.
    double=send(qr['amarillo'],company_id,mismatch_event)
    assert double.status_code==409, double.text
    different=send(other_qr,other_id,mismatch_event,"999")
    assert different.status_code==409, different.text
    after=client.get(f'/api/v1/trips/{trip}/manifest',headers=admin).json()
    assert after['weighed_total']==2 and after['plant_total']==2
    assert sum(1 for r in after['rows'] if r['weighed_count']==1)==2
