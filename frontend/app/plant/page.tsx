"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Factory, Scale, ScanLine } from "lucide-react";
import AppShell from "@/components/AppShell";
import Scanner from "@/components/Scanner";
import { api, Manifest, Trip, colorMeta } from "@/lib/api";

export default function PlantPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [weightPayload, setWeightPayload] = useState("");
  const [weight, setWeight] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const loadManifest = (id:number)=>api<Manifest>(`/trips/${id}/manifest`).then(setManifest);

  useEffect(()=>{
    api<Trip[]>("/trips").then(t=>{
      setTrips(t);
      const active=t.find(x=>x.status!=="closed");
      if(active)setSelected(active.id);
    });
  },[]);

  useEffect(()=>{if(selected)loadManifest(selected);},[selected]);

  const receptionComplete = Boolean(
    manifest && manifest.pickup_total > 0 && manifest.plant_total >= manifest.pickup_total
  );
  const weighingCaughtUp = Boolean(
    manifest && manifest.plant_total > 0 && manifest.weighed_total >= manifest.plant_total
  );
  const canReceive = Boolean(selected && manifest && manifest.pickup_total > 0 && !receptionComplete);
  const canStartWeighing = Boolean(selected && manifest && manifest.plant_total > 0 && !weighingCaughtUp);

  async function receive(payload:string){
    if(!selected)return;
    setError("");
    try{
      const r=await api<{
        company_name:string;
        color:"amarillo"|"verde"|"azul";
        registered_count:number;
        limit_count:number|null;
        remaining_count:number|null;
      }>(`/trips/${selected}/scan`,{
        method:"POST",
        body:JSON.stringify({qr_payload:payload,stage:"plant",client_event_id:crypto.randomUUID()})
      });
      const limit = r.limit_count ?? 0;
      const completed = r.remaining_count === 0;
      setNotice(`✓ ${r.company_name} · ${colorMeta[r.color].label} · recepción ${r.registered_count}/${limit}${completed ? " · cupo completo" : ""}`);
      await loadManifest(selected);
    }catch(e){
      setError(e instanceof Error?e.message:"Error");
      await loadManifest(selected);
    }
  }

  async function weigh(){
    if(!selected||!weightPayload||!weight)return;
    setError("");
    try{
      const r=await api<{
        company_name:string;
        color:"amarillo"|"verde"|"azul";
        weight_kg:string;
        weighed_count:number;
        limit_count:number;
        remaining_count:number;
      }>(`/trips/${selected}/weighings`,{
        method:"POST",
        body:JSON.stringify({qr_payload:weightPayload,weight_kg:Number(weight),client_event_id:crypto.randomUUID()})
      });
      const completed = r.remaining_count === 0;
      setNotice(`✓ ${r.company_name} · ${colorMeta[r.color].label} · ${Number(r.weight_kg).toFixed(3)} kg · pesaje ${r.weighed_count}/${r.limit_count}${completed ? " · cupo completo" : ""}`);
      setWeightPayload("");
      setWeight("");
      await loadManifest(selected);
    }catch(e){
      setError(e instanceof Error?e.message:"Error");
      await loadManifest(selected);
    }
  }

  return <AppShell><div className="page-wrap">
    <div className="page-header"><div><span className="eyebrow">PLANTA DE RECICLAJE</span><h1>Recepción y pesaje</h1><p>Conciliá las bolsas declaradas y registrá el peso individual.</p></div><Factory size={28}/></div>

    <div className="panel"><label className="select-label">Manifiesto / viaje<select value={selected??""} onChange={e=>setSelected(Number(e.target.value))}><option value="">Seleccionar</option>{trips.filter(t=>t.status!=="closed").map(t=><option key={t.id} value={t.id}>{t.route_code} · {t.vehicle} · {t.collector_name}</option>)}</select></label></div>

    {notice&&<div className="alert success">{notice}</div>}
    {error&&<div className="alert error">{error}</div>}

    {manifest && <div className="plant-progress-grid">
      <div className={receptionComplete ? "progress-card done" : "progress-card"}>
        <span>Recepción</span>
        <b>{manifest.plant_total} / {manifest.pickup_total}</b>
        <small>{receptionComplete ? "Recepción completa" : `${Math.max(0, manifest.pickup_total-manifest.plant_total)} pendientes`}</small>
      </div>
      <div className={manifest.plant_total > 0 && manifest.weighed_total >= manifest.plant_total ? "progress-card done" : "progress-card"}>
        <span>Pesaje</span>
        <b>{manifest.weighed_total} / {manifest.plant_total}</b>
        <small>{manifest.plant_total===0 ? "Sin bolsas recibidas" : weighingCaughtUp ? "Todo lo recibido está pesado" : `${Math.max(0, manifest.plant_total-manifest.weighed_total)} pendientes`}</small>
      </div>
    </div>}

    <div className="two-col align-start">
      <div className="panel">
        <div className="section-title"><div><h2><ScanLine size={20}/> 1. Recepción</h2><p>Volvé a escanear cada bolsa descargada. Nunca puede superar lo retirado.</p></div></div>
        {receptionComplete ? <div className="stage-complete"><CheckCircle2 size={20}/><div><b>Recepción completa</b><span>Ya se verificaron todas las bolsas declaradas por el recolector.</span></div></div> :
          <Scanner onScan={receive} disabled={!canReceive} buttonLabel="Abrir cámara para recepción"/>}
        {manifest && manifest.pickup_total===0 && <div className="stage-note">Este viaje todavía no tiene bolsas recolectadas.</div>}
      </div>

      <div className="panel">
        <div className="section-title"><div><h2><Scale size={20}/> 2. Pesaje individual</h2><p>Escaneá el QR y cargá el peso de esa bolsa. Nunca puede superar lo recibido.</p></div></div>
        {weighingCaughtUp && manifest && manifest.plant_total>0 ? <div className="stage-complete"><CheckCircle2 size={20}/><div><b>Pesaje al día</b><span>No quedan bolsas recibidas pendientes de peso.</span></div></div> :
          <Scanner onScan={payload=>setWeightPayload(payload)} disabled={!canStartWeighing} buttonLabel="Abrir cámara para pesaje"/>}
        {manifest && manifest.plant_total===0 && <div className="stage-note">Primero verificá al menos una bolsa en recepción.</div>}
        {weightPayload&&<div className="weight-box"><div className="success-chip">QR listo para pesar</div><label>Peso de la bolsa (kg)<input type="number" step="0.001" min="0.001" value={weight} onChange={e=>setWeight(e.target.value)} placeholder="12.500" autoFocus/></label><button className="primary-btn wide" onClick={weigh} disabled={!weight}>Registrar peso</button></div>}
      </div>
    </div>

    {manifest&&<div className="panel table-panel"><div className="table-head"><div><h2>Conciliación del viaje</h2><p>Recolector vs. planta vs. pesaje</p></div><div className={manifest.difference_total===0?"status-pill":"status-pill warn"}>{manifest.difference_total===0?"Sin diferencias":`${manifest.difference_total} de diferencia`}</div></div><div className="data-table"><div className="tr th"><div>Empresa</div><div>Color</div><div>Retiradas</div><div>Planta</div><div>Pesadas</div><div>Kg</div></div>{manifest.rows.map((r,i)=><div className="tr six" key={`${r.company_id}-${r.color}-${i}`}><div><b>{r.company_name}</b></div><div><span className={`dot ${colorMeta[r.color].className}`}/>{colorMeta[r.color].label}</div><div>{r.pickup_count}</div><div className={r.plant_count===r.pickup_count?"ok-text":r.plant_count>r.pickup_count?"bad-text":""}>{r.plant_count}</div><div className={r.weighed_count===r.plant_count&&r.plant_count>0?"ok-text":""}>{r.weighed_count}</div><div><b>{Number(r.total_kg).toFixed(3)}</b></div></div>)}</div></div>}
  </div></AppShell>;
}
