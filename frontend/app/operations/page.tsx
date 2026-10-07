"use client";

import { useEffect, useState } from "react";
import { Plus, Route, ScanLine, Truck } from "lucide-react";
import AppShell from "@/components/AppShell";
import Scanner from "@/components/Scanner";
import { api, Manifest, Trip, colorMeta } from "@/lib/api";

export default function OperationsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [form, setForm] = useState({ vehicle: "", collector_name: "" });
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const loadTrips = () => api<Trip[]>("/trips").then(t => { setTrips(t); if (!selected && t[0]) setSelected(t[0].id); });
  const loadManifest = (id: number) => api<Manifest>(`/trips/${id}/manifest`).then(setManifest);
  useEffect(() => { loadTrips(); }, []);
  useEffect(() => { if (selected) loadManifest(selected); }, [selected]);

  async function createTrip(e: React.FormEvent) { e.preventDefault(); setError(""); try { const trip = await api<Trip>("/trips", { method:"POST", body:JSON.stringify(form) }); setForm({vehicle:"",collector_name:""}); await loadTrips(); setSelected(trip.id); } catch(e){ setError(e instanceof Error?e.message:"Error"); } }
  async function scan(payload: string) { if (!selected) return; setError(""); try { const r = await api<{company_name:string;color:"amarillo"|"verde"|"azul";registered_count:number}>(`/trips/${selected}/scan`, { method:"POST", body:JSON.stringify({qr_payload:payload,stage:"pickup",client_event_id:crypto.randomUUID()}) }); setNotice(`✓ ${r.company_name} · ${colorMeta[r.color].label} · bolsa #${r.registered_count} registrada`); await loadManifest(selected); } catch(e){ setError(e instanceof Error?e.message:"Error"); if(selected) await loadManifest(selected); } }

  return <AppShell><div className="page-wrap">
    <div className="page-header"><div><span className="eyebrow">RECOLECCIÓN</span><h1>Retiro y carga al camión</h1><p>Cada lectura del QR suma una bolsa al manifiesto digital.</p></div></div>
    <div className="ops-grid"><div className="panel"><div className="section-title"><div><h2>Nuevo viaje</h2><p>Identificá el vehículo y el recolector.</p></div><Truck size={20}/></div><form className="stack-form" onSubmit={createTrip}><label>Patente / vehículo<input required value={form.vehicle} onChange={e=>setForm({...form,vehicle:e.target.value})} placeholder="AC 123 BD"/></label><label>Recolector<input required value={form.collector_name} onChange={e=>setForm({...form,collector_name:e.target.value})} placeholder="Juan Pérez"/></label><button className="primary-btn"><Plus size={16}/> Iniciar recorrido</button></form></div>
      <div className="panel"><div className="section-title"><div><h2>Viaje activo</h2><p>Seleccioná el manifiesto que estás cargando.</p></div><Route size={20}/></div><select value={selected ?? ""} onChange={e=>setSelected(Number(e.target.value))}><option value="">Seleccionar viaje</option>{trips.filter(t=>t.status!=="closed").map(t=><option key={t.id} value={t.id}>{t.route_code} · {t.vehicle}</option>)}</select>{manifest && <div className="trip-summary"><div><span>Recolector</span><b>{manifest.trip.collector_name}</b></div><div><span>Bolsa retiradas</span><b>{manifest.pickup_total}</b></div><div><span>Estado</span><b>{manifest.trip.status}</b></div></div>}</div></div>
    {notice && <div className="alert success">{notice}</div>}{error && <div className="alert error">{error}</div>}
    <div className="panel"><div className="section-title"><div><h2><ScanLine size={20}/> Escanear bolsas</h2><p>El mismo QR puede leerse muchas veces: una lectura = una bolsa.</p></div></div><Scanner onScan={scan} disabled={!selected}/></div>
    {manifest && <div className="panel table-panel"><div className="table-head"><div><h2>Manifiesto de recolección</h2><p>{manifest.trip.route_code}</p></div><div className="big-inline">{manifest.pickup_total} <span>bolsas</span></div></div><div className="data-table"><div className="tr th"><div>Empresa</div><div>Color</div><div>Material</div><div>Retiradas</div><div>Recibidas</div></div>{manifest.rows.map((r,i)=><div className="tr" key={`${r.company_id}-${r.color}-${i}`}><div><b>{r.company_name}</b></div><div><span className={`dot ${colorMeta[r.color].className}`}/>{colorMeta[r.color].label}</div><div>{r.material_name}</div><div><b>{r.pickup_count}</b></div><div>{r.plant_count}</div></div>)}</div></div>}
  </div></AppShell>;
}
