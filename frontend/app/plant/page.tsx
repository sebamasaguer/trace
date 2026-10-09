"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Factory, Scale, ShieldCheck } from "lucide-react";
import AppShell from "@/components/AppShell";
import Scanner from "@/components/Scanner";
import { api, Manifest, Trip, WasteColor, colorMeta } from "@/lib/api";

type LabelInfo = { company_id: number; company_name: string; color: WasteColor; material_name: string; public_code: string };

export default function PlantPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [weightPayload, setWeightPayload] = useState("");
  const [labelInfo, setLabelInfo] = useState<LabelInfo | null>(null);
  const [weight, setWeight] = useState("");
  const [saving, setSaving] = useState(false);
  const submitInFlight = useRef(false);
  const pendingEventId = useRef<string | null>(null);
  const activeCompanyRef = useRef<number | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const loadManifest = (id: number) => api<Manifest>(`/trips/${id}/manifest`).then(setManifest);

  useEffect(() => {
    api<Trip[]>("/trips").then(t => {
      setTrips(t);
      const active = t.find(x => x.status !== "closed");
      if (active) setSelected(active.id);
    }).catch(e => setError(e instanceof Error ? e.message : "Error al cargar viajes"));
  }, []);

  useEffect(() => {
    setWeightPayload(""); setLabelInfo(null); setWeight(""); setNotice(""); setError(""); setManifest(null); setSelectedCompanyId(null);
    pendingEventId.current=null; activeCompanyRef.current=null;
    if (selected) loadManifest(selected).catch(e => setError(e instanceof Error ? e.message : "Error al cargar manifiesto"));
  }, [selected]);

  const availableCompanies = Array.from(new Map(
    (manifest?.rows ?? []).filter(r => r.pickup_count > 0).map(r => [r.company_id, r.company_name] as const)
  )).map(([id, name]) => ({ id, name })).sort((a,b) => a.name.localeCompare(b.name));
  const selectedCompany = availableCompanies.find(c => c.id === selectedCompanyId);
  const companyRows = (manifest?.rows ?? []).filter(r => r.company_id === selectedCompanyId);
  const picked = companyRows.reduce((sum, r) => sum + r.pickup_count, 0);
  const weighed = companyRows.reduce((sum, r) => sum + r.weighed_count, 0);
  const finished = Boolean(selectedCompanyId) && picked > 0 && weighed >= picked;
  const pending = Math.max(0, picked - weighed);
  const currentRow = labelInfo && companyRows.find(r => r.color === labelInfo.color);
  const colorCompleted = Boolean(currentRow && currentRow.weighed_count >= currentRow.pickup_count);
  const notInTrip = Boolean(labelInfo && !currentRow);

  function selectCompany(value: string) {
    const nextId = value ? Number(value) : null;
    if (nextId === selectedCompanyId) return;
    if (weightPayload && !window.confirm("Hay una bolsa escaneada sin confirmar. ¿Descartar ese pesaje y cambiar de empresa?")) return;
    activeCompanyRef.current=nextId;
    setSelectedCompanyId(nextId);
    setWeightPayload(""); setLabelInfo(null); setWeight(""); setNotice(""); setError(""); pendingEventId.current=null;
  }

  async function scanForWeight(payload: string) {
    setError(""); setNotice(""); setWeight(""); setWeightPayload(""); setLabelInfo(null); pendingEventId.current=null;
    if (!selected || !manifest || !selectedCompanyId) {
      setError("Seleccioná primero la empresa que estás pesando.");
      return;
    }
    try {
      const label = await api<LabelInfo>(`/companies/verify/label?payload=${encodeURIComponent(payload)}`);
      // Ignorar lecturas en vuelo si el operador cambió la empresa mientras se validaba.
      if (activeCompanyRef.current !== selectedCompanyId) return;
      if (label.company_id !== selectedCompanyId) {
        throw new Error(`EMPRESA INCORRECTA: este QR corresponde a ${label.company_name}, pero estás pesando ${selectedCompany?.name ?? "otra empresa"}. No se registró ninguna bolsa.`);
      }
      const row = companyRows.find(r => r.color === label.color);
      if (!row || row.pickup_count === 0) {
        throw new Error("Esta empresa y color no tienen bolsas recolectadas en el viaje seleccionado.");
      }
      if (row.weighed_count >= row.pickup_count) {
        throw new Error(`Ya se pesaron las ${row.pickup_count} bolsas recolectadas de ${label.company_name} · ${colorMeta[label.color].label}.`);
      }
      setWeightPayload(payload);
      pendingEventId.current=crypto.randomUUID();
      setLabelInfo(label);
    } catch (e) {
      setError(e instanceof Error ? e.message : "QR no válido");
    }
  }

  async function weigh() {
    const n = Number(weight);
    if (!selected || !selectedCompanyId || !weightPayload || !labelInfo || labelInfo.company_id !== selectedCompanyId || !Number.isFinite(n) || n <= 0 || n>10000 || saving || submitInFlight.current || colorCompleted || notInTrip) return;
    submitInFlight.current=true;
    if (!pendingEventId.current) pendingEventId.current=crypto.randomUUID();
    setSaving(true); setError(""); setNotice("");
    try {
      const r = await api<{ company_name:string; color:WasteColor; weight_kg:string; weighed_count:number; limit_count:number; remaining_count:number }>(
        `/trips/${selected}/weighings`, {
          method: "POST",
          body: JSON.stringify({ qr_payload:weightPayload, company_id:selectedCompanyId, weight_kg:n, client_event_id:pendingEventId.current })
        }
      );
      setNotice(`✓ ${r.company_name} · ${colorMeta[r.color].label} · ${Number(r.weight_kg).toFixed(3)} kg · ${r.weighed_count}/${r.limit_count} bolsas pesadas y recibidas${r.remaining_count===0 ? " · completo" : ""}`);
      setWeightPayload(""); setLabelInfo(null); setWeight(""); pendingEventId.current=null;
      await loadManifest(selected);
    } catch(e) {
      setError(e instanceof Error ? e.message : "No se pudo registrar el pesaje");
      await loadManifest(selected).catch(() => {});
    } finally { submitInFlight.current=false; setSaving(false); }
  }

  return <AppShell><div className="page-wrap">
    <div className="page-header"><div><span className="eyebrow">PLANTA DE RECICLAJE</span><h1>Pesaje de bolsas</h1><p>La bolsa se recibe en planta en el mismo momento en que se confirma su peso. No hay recepción previa.</p></div><Factory size={28}/></div>

    <div className="panel"><label className="select-label">Manifiesto / viaje<select value={selected??""} onChange={e => setSelected(e.target.value ? Number(e.target.value) : null)}><option value="">Seleccionar viaje</option>{trips.filter(t=>t.status!=="closed").map(t=><option key={t.id} value={t.id}>{t.route_code} · {t.vehicle} · {t.collector_name}</option>)}</select></label></div>

    {manifest && <div className="panel rt-company-focus-panel">
      <label className="select-label" htmlFor="company-at-scale">Empresa que se está pesando</label>
      <select id="company-at-scale" className="rt-company-focus-select" disabled={saving} value={selectedCompanyId ?? ""} onChange={e => selectCompany(e.target.value)}>
        <option value="">Seleccionar empresa del viaje</option>
        {availableCompanies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      {selectedCompany ? <div className="rt-active-company" role="status"><ShieldCheck size={20}/><span>EMPRESA ACTIVA<strong>{selectedCompany.name}</strong><small>Solo se admiten QR de esta empresa. Cambiar requiere selección explícita.</small></span></div> :
        <div className="stage-note">Seleccioná una empresa antes de abrir la cámara. No se puede pesar una bolsa sin identificar a su cliente.</div>}
    </div>}

    {error && !manifest && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    {manifest && selectedCompany && <div className="plant-progress-grid">
      <div className="progress-card"><span>Recolectadas</span><b>{picked}</b><small>Bolsa(s) declaradas en el viaje</small></div>
      <div className={finished ? "progress-card done" : "progress-card"}><span>Recibidas y pesadas</span><b>{weighed} / {picked}</b><small>{finished ? "Todas las bolsas están pesadas" : `${pending} pendientes de pesar`}</small></div>
    </div>}

    <div className="panel rt-plant-action">
      <div className="section-title"><div><h2><Scale size={20}/> Escanear y pesar en una sola operación</h2><p>Leé el QR, colocá la bolsa en la balanza y confirmá los kilos. Se registra simultáneamente recepción + pesaje.</p></div><ShieldCheck size={20}/></div>
      {error && <div className="alert error" role="alert">{error}</div>}
      {finished ? <div className="stage-complete"><CheckCircle2 size={20}/><div><b>Empresa completamente pesada</b><span>Todas las bolsas recolectadas de esta empresa fueron pesadas; no se permiten más registros.</span></div></div> :
        <Scanner key={`${selected ?? "empty"}-${selectedCompanyId ?? "none"}`} onScan={scanForWeight} disabled={!selected || !manifest || !selectedCompanyId || picked===0 || saving || Boolean(weightPayload)} buttonLabel="Abrir cámara para escanear bolsa" />}
      {manifest && manifest.pickup_total===0 && <div className="stage-note">Todavía no hay bolsas recolectadas en este viaje.</div>}
      {manifest && !selectedCompanyId && <div className="stage-note">Para habilitar el escáner seleccioná primero la empresa en el panel superior.</div>}
      {labelInfo && weightPayload && <div className="rt-weigh-entry">
        <div className="rt-weigh-bag"><div><span className={`dot ${colorMeta[labelInfo.color].className}`}/><strong>{labelInfo.company_name}</strong><small>{labelInfo.material_name} · {colorMeta[labelInfo.color].label}</small></div><span className="status-pill">{currentRow?.weighed_count ?? 0} / {currentRow?.pickup_count ?? 0} pesadas</span></div>
        <label>Peso de esta bolsa (kg)<input type="number" inputMode="decimal" step="0.001" min="0.001" max="10000" value={weight} onChange={e=>setWeight(e.target.value)} placeholder="Ej.: 12.500" autoFocus /></label>
        <div className="rt-weigh-actions"><button className="ghost-btn" type="button" disabled={saving} onClick={()=>{setWeightPayload("");setWeight("");setLabelInfo(null);pendingEventId.current=null}}>Cancelar</button><button className="primary-btn" type="button" disabled={saving || colorCompleted || !weight || !Number.isFinite(Number(weight)) || Number(weight)<=0 || Number(weight)>10000} onClick={weigh}>{saving ? "Registrando..." : "Confirmar recepción y pesaje"}</button></div>
      </div>}
    </div>

    {manifest && <div className="panel table-panel"><div className="table-head"><div><h2>Control del manifiesto</h2><p>{selectedCompany ? `Solo ${selectedCompany.name} · recolectadas vs. pesadas` : "Seleccioná una empresa para ver su manifiesto"}</p></div>{selectedCompany && <div className={pending===0 ? "status-pill" : "status-pill warn"}>{pending===0 ? "Conciliado" : `${pending} pendientes`}</div>}</div><div className="rt-table-scroll"><div className="data-table"><div className="tr rt-four-col th"><div>Empresa</div><div>Color</div><div>Recolectadas</div><div>Recibidas y pesadas</div></div>{companyRows.map((r,i)=><div className="tr rt-four-col" key={`${r.company_id}-${r.color}-${i}`}><div><b>{r.company_name}</b><small>{r.material_name}</small></div><div><span className={`dot ${colorMeta[r.color].className}`}/>{colorMeta[r.color].label}</div><div>{r.pickup_count}</div><div><b className={r.weighed_count===r.pickup_count ? "ok-text" : ""}>{r.weighed_count} / {r.pickup_count}</b><small>{Number(r.total_kg).toFixed(3)} kg</small></div></div>)}</div></div></div>}
  </div></AppShell>;
}
