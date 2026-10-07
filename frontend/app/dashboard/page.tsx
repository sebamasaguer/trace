"use client";

import { useEffect, useState } from "react";
import { Building2, CircleAlert, PackageCheck, Recycle, Route, Scale } from "lucide-react";
import AppShell from "@/components/AppShell";
import KpiCard from "@/components/KpiCard";
import { api } from "@/lib/api";

type Dashboard = { active_companies: number; open_trips: number; bags_collected_today: number; bags_received_today: number; kg_today: string | number; kg_month: string | number; mismatch_count: number };

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<Dashboard>("/dashboard").then(setData).catch(e => setError(e.message)); }, []);
  return <AppShell><div className="page-wrap">
    <div className="page-header"><div><span className="eyebrow">OPERACIÓN EN TIEMPO REAL</span><h1>Resumen general</h1><p>Estado de recolección, recepción y pesaje.</p></div><div className="status-pill"><span className="pulse"/> Sistema operativo</div></div>
    {error && <div className="alert error">{error}</div>}
    <div className="kpi-grid">
      <KpiCard label="Empresas activas" value={data?.active_companies ?? "—"} icon={Building2}/>
      <KpiCard label="Viajes abiertos" value={data?.open_trips ?? "—"} icon={Route}/>
      <KpiCard label="Bolsas retiradas hoy" value={data?.bags_collected_today ?? "—"} icon={Recycle}/>
      <KpiCard label="Bolsas recibidas hoy" value={data?.bags_received_today ?? "—"} icon={PackageCheck}/>
      <KpiCard label="Kg procesados hoy" value={data ? `${Number(data.kg_today).toFixed(2)} kg` : "—"} icon={Scale}/>
      <KpiCard label="Viajes con diferencia" value={data?.mismatch_count ?? "—"} sub="Requieren conciliación" icon={CircleAlert}/>
    </div>
    <div className="two-col">
      <div className="panel hero-panel"><span className="eyebrow">MODELO OPERATIVO</span><h2>3 QR por empresa. Miles de movimientos.</h2><p>Cada cliente imprime un QR amarillo, uno verde y uno azul. Cada lectura crea un evento de bolsa sin necesidad de administrar códigos unitarios.</p><div className="color-flow"><div className="color-dot yellow">A</div><div className="color-dot green">V</div><div className="color-dot blue">A</div><span>→</span><b>Retiro</b><span>→</span><b>Planta</b><span>→</span><b>Pesaje</b></div></div>
      <div className="panel"><span className="eyebrow">ACUMULADO DEL MES</span><div className="big-number">{data ? Number(data.kg_month).toLocaleString("es-AR", { maximumFractionDigits: 2 }) : "—"}<small> kg</small></div><p>Material reciclable pesado y registrado durante el mes corriente.</p></div>
    </div>
  </div></AppShell>;
}
