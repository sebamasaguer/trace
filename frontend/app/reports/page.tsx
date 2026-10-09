"use client";

import { useEffect, useMemo, useState } from "react";
import { BarChart3, CalendarDays, Download, Printer } from "lucide-react";
import AppShell from "@/components/AppShell";
import { api, Company, WasteColor, colorMeta } from "@/lib/api";

type Period = "day" | "week" | "month" | "year";
type ColorRow = { color:WasteColor; material_name:string; collected:number; weighed:number; kg:string|number };
type TimeRow = { period:string; collected:number; weighed:number; kg:string|number };
type CompanyReport = {
  company_id:number; company_name:string; period:Period; reference_date:string;
  start_date:string; end_date_exclusive:string; timezone:string;
  collected_total:number; weighed_total:number; kg_total:string|number;
  colors:ColorRow[]; timeline:TimeRow[];
};

const periods: {value:Period;label:string}[] = [
  {value:"day",label:"Diario"}, {value:"week",label:"Semanal"},
  {value:"month",label:"Mensual"}, {value:"year",label:"Anual"}
];

const formatKg = (v: string|number) => Number(v).toLocaleString("es-AR", {minimumFractionDigits:3,maximumFractionDigits:3});
const todayInSalta = () => new Intl.DateTimeFormat("en-CA", {timeZone:"America/Argentina/Salta",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
function downloadCsv(report: CompanyReport) {
  const escapeCsv=(v:unknown) => { const raw=String(v ?? ""); const safe=/^[=+@\-\t\r]/.test(raw) ? "'"+raw : raw; return `"${safe.replace(/"/g,'""')}"`; };
  const lines:unknown[][]=[
    ["Empresa",report.company_name],["Desde",report.start_date],["Hasta exclusivo",report.end_date_exclusive],
    ["Zona horaria",report.timezone],[],
    ["Material","Color","Bolsas recolectadas","Bolsas recibidas y pesadas","Kilos pesados"],
    ...report.colors.map(r=>[r.material_name,colorMeta[r.color].label,r.collected,r.weighed,formatKg(r.kg)]),
    ["TOTAL","",report.collected_total,report.weighed_total,formatKg(report.kg_total)],[],
    ["Periodo","Bolsas recolectadas","Bolsas recibidas y pesadas","Kilos pesados"],
    ...report.timeline.map(r=>[r.period,r.collected,r.weighed,formatKg(r.kg)])
  ];
  const csv="\uFEFF"+lines.map(line=>line.map(escapeCsv).join(";")).join("\r\n");
  const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");a.href=url;a.download=`reciclatrace_${report.company_id}_${report.period}_${report.reference_date}.csv`;a.click();
  URL.revokeObjectURL(url);
}

export default function CompanyReportsPage() {
  const [companies,setCompanies]=useState<Company[]>([]);
  const [company,setCompany]=useState("");
  const [period,setPeriod]=useState<Period>("month");
  const [reference,setReference]=useState(todayInSalta);
  const [report,setReport]=useState<CompanyReport|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");

  useEffect(()=>{
    api<Company[]>("/companies").then(c=>{setCompanies(c);if(c.length)setCompany(String(c[0].id));})
      .catch(e=>setError(e instanceof Error?e.message:"No se pudieron cargar las empresas"));
  },[]);
  useEffect(()=>{
    if(!company){setReport(null);return;}
    let alive=true;
    setLoading(true);setError("");setReport(null);
    api<CompanyReport>(`/reports/company/${company}?period=${period}&reference_date=${reference}`)
      .then(r=>{if(alive)setReport(r)})
      .catch(e=>{if(alive)setError(e instanceof Error?e.message:"Error al consultar reporte")})
      .finally(()=>{if(alive)setLoading(false)});
    return ()=>{alive=false};
  },[company,period,reference]);

  const maxKg = useMemo(()=>Math.max(1,...(report?.timeline??[]).map(r=>Number(r.kg))),[report]);

  return <AppShell><div className="page-wrap rt-report-page">
    <div className="page-header"><div><span className="eyebrow">ANÁLISIS Y ESTADÍSTICAS</span><h1>Reportes por empresa</h1><p>Consultá cantidades recolectadas y kilos pesados por día, semana, mes o año.</p></div><BarChart3 size={28}/></div>

    <div className="panel rt-report-filters no-print">
      <label>Empresa<select value={company} onChange={e=>setCompany(e.target.value)}><option value="">Seleccionar empresa</option>{companies.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
      <label>Período<select value={period} onChange={e=>setPeriod(e.target.value as Period)}>{periods.map(p=><option key={p.value} value={p.value}>{p.label}</option>)}</select></label>
      <label>Fecha de referencia<input type="date" value={reference} onChange={e=>setReference(e.target.value)}/></label>
      <div className="rt-report-export"><button className="ghost-btn" disabled={!report} onClick={()=>report&&downloadCsv(report)}><Download size={16}/> CSV</button><button className="ghost-btn" disabled={!report} onClick={()=>window.print()}><Printer size={16}/> Imprimir / PDF</button></div>
    </div>

    {loading && <div className="panel rt-report-message">Consultando registros...</div>}
    {error && <div className="alert error" role="alert">{error}</div>}
    {!company && !error && <div className="panel rt-report-message">Seleccioná una empresa para ver sus movimientos.</div>}

    {report && <>
      <div className="rt-report-title"><div><span className="eyebrow">INFORME DE RECICLAJE</span><h2>{report.company_name}</h2><p><CalendarDays size={15}/> {report.start_date} al día anterior a {report.end_date_exclusive} · Horario de Salta (UTC−3)</p></div><span className="status-pill">{periods.find(p=>p.value===period)?.label}</span></div>
      <div className="kpi-grid rt-report-kpis"><div className="kpi-card"><span>Bolsas recolectadas</span><strong>{report.collected_total.toLocaleString("es-AR")}</strong><small>Registradas por los recolectores en el período</small></div><div className="kpi-card"><span>Bolsas recibidas y pesadas</span><strong>{report.weighed_total.toLocaleString("es-AR")}</strong><small>Pesajes confirmados en la planta</small></div><div className="kpi-card"><span>Kilogramos reciclados</span><strong>{formatKg(report.kg_total)}</strong><small>kg netos registrados</small></div></div>

      <div className="panel table-panel"><div className="table-head"><div><h2>Desglose por tipo de residuo</h2><p>Bolsas y peso total por color de QR</p></div></div><div className="rt-table-scroll"><div className="data-table"><div className="tr rt-report-color-row th"><div>Material</div><div>Color</div><div>Recolectadas</div><div>Recibidas y pesadas</div><div>Kg</div></div>{report.colors.map(r=><div className="tr rt-report-color-row" key={r.color}><div><b>{r.material_name}</b></div><div><span className={`dot ${colorMeta[r.color].className}`}/>{colorMeta[r.color].label}</div><div>{r.collected}</div><div>{r.weighed}</div><div><b>{formatKg(r.kg)}</b></div></div>)}</div></div></div>

      <div className="panel rt-chart-panel"><div className="section-title"><div><h2>Evolución del reciclaje</h2><p>Kilogramos procesados en el período seleccionado</p></div></div><div className="rt-chart-list">{report.timeline.map(row=><div className="rt-chart-row" key={row.period}><span>{row.period}</span><div className="rt-chart-track"><div className="rt-chart-fill" style={{width:`${Number(row.kg)>0? Math.max(1.5,Number(row.kg)/maxKg*100):0}%`}}/></div><strong>{formatKg(row.kg)} kg</strong></div>)}</div></div>

      <div className="panel table-panel"><div className="table-head"><div><h2>Detalle por período</h2><p>{period==="year"?"Desglose mensual":"Desglose diario"}</p></div></div><div className="rt-table-scroll"><div className="data-table"><div className="tr rt-report-timeline-row th"><div>Fecha / período</div><div>Recolectadas</div><div>Recibidas y pesadas</div><div>Kg</div></div>{report.timeline.map(row=><div className="tr rt-report-timeline-row" key={row.period}><div><b>{row.period}</b></div><div>{row.collected}</div><div>{row.weighed}</div><div><b>{formatKg(row.kg)}</b></div></div>)}</div></div></div>
      <p className="rt-report-footnote">Nota: las bolsas recolectadas se agrupan por la fecha del retiro y los kilos por la fecha del pesaje. Si una bolsa se retira un día y se pesa otro, aparecerá en períodos diferentes. La conciliación exacta se consulta en Trazabilidad por viaje.</p>
    </>}
  </div></AppShell>;
}
