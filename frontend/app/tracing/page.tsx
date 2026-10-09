"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, FileCheck2 } from "lucide-react";
import AppShell from "@/components/AppShell";
import { api, Manifest, Trip, colorMeta } from "@/lib/api";

export default function ReportsPage(){
 const [trips,setTrips]=useState<Trip[]>([]); const [selected,setSelected]=useState<number|null>(null); const [manifest,setManifest]=useState<Manifest|null>(null); const [error,setError]=useState("");
 useEffect(()=>{api<Trip[]>("/trips").then(t=>{setTrips(t);if(t[0])setSelected(t[0].id)}).catch(e=>setError(e.message));},[]);
 useEffect(()=>{if(selected)api<Manifest>(`/trips/${selected}/manifest`).then(setManifest).catch(e=>setError(e.message));},[selected]);
 return <AppShell><div className="page-wrap"><div className="page-header"><div><span className="eyebrow">CONTROL Y AUDITORÍA</span><h1>Trazabilidad del manifiesto</h1><p>Vista consolidada por empresa, color, cantidades y kilos.</p></div><FileCheck2 size={28}/></div>
 <div className="panel"><label className="select-label">Seleccionar viaje<select value={selected??""} onChange={e=>setSelected(Number(e.target.value))}>{trips.map(t=><option key={t.id} value={t.id}>{t.route_code} · {t.vehicle} · {t.status}</option>)}</select></label></div>{error&&<div className="alert error">{error}</div>}
 {manifest&&<><div className="kpi-grid four"><div className="kpi-card"><span>Retiradas</span><strong>{manifest.pickup_total}</strong></div><div className="kpi-card"><span>Recibidas y pesadas</span><strong>{manifest.weighed_total}</strong></div><div className="kpi-card"><span>Pendientes de pesaje</span><strong>{Math.max(0,manifest.pickup_total-manifest.weighed_total)}</strong></div><div className="kpi-card"><span>Kilos</span><strong>{Number(manifest.kg_total).toFixed(3)}</strong></div></div><div className="panel table-panel"><div className="table-head"><div><h2>{manifest.trip.route_code}</h2><p>{manifest.trip.vehicle} · {manifest.trip.collector_name}</p></div>{manifest.pickup_total===manifest.weighed_total?<div className="status-pill"><CheckCircle2 size={15}/> Conciliado</div>:<div className="status-pill warn"><CircleAlert size={15}/> Revisar diferencia</div>}</div><div className="data-table"><div className="tr th"><div>Empresa</div><div>Color</div><div>Retiro</div><div>Pesadas</div><div>Diferencia</div><div>Kg</div></div>{manifest.rows.map((r,i)=><div className="tr six" key={i}><div><b>{r.company_name}</b><small>{r.material_name}</small></div><div><span className={`dot ${colorMeta[r.color].className}`}/>{colorMeta[r.color].label}</div><div>{r.pickup_count}</div><div>{r.weighed_count}</div><div className={r.pickup_count===r.weighed_count?"ok-text":"bad-text"}>{r.pickup_count===r.weighed_count?"0 ✓":r.weighed_count-r.pickup_count}</div><div><b>{Number(r.total_kg).toFixed(3)}</b></div></div>)}</div></div></>}
 </div></AppShell>
}
