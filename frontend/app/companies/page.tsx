"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Building2, Plus, Printer, QrCode } from "lucide-react";
import AppShell from "@/components/AppShell";
import { api, Company } from "@/lib/api";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", tax_id: "", site_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api<Company[]>("/companies").then(setCompanies).catch(e => setError(e.message));
  useEffect(() => {
    void load();
  }, []);
  async function create(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { await api("/companies", { method: "POST", body: JSON.stringify(form) }); setForm({ name: "", tax_id: "", site_name: "" }); setShowForm(false); load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }

  return <AppShell><div className="page-wrap">
    <div className="page-header"><div><span className="eyebrow">MAESTRO DE CLIENTES</span><h1>Empresas y etiquetas QR</h1><p>Cada empresa dispone exactamente de tres QR permanentes: amarillo, verde y azul.</p></div><button className="primary-btn" onClick={() => setShowForm(v => !v)}><Plus size={17}/> Nueva empresa</button></div>
    {error && <div className="alert error">{error}</div>}
    {showForm && <form className="panel inline-form" onSubmit={create}><label>Razón social<input required value={form.name} onChange={e => setForm({...form, name:e.target.value})}/></label><label>CUIT<input value={form.tax_id} onChange={e => setForm({...form, tax_id:e.target.value})}/></label><label>Sucursal<input value={form.site_name} onChange={e => setForm({...form, site_name:e.target.value})}/></label><button className="primary-btn" disabled={busy}>{busy ? "Guardando..." : "Crear y generar 3 QR"}</button></form>}
    <div className="panel table-panel rt-companies-panel">
      <div className="table-head"><div><h2>Clientes registrados</h2><p>{companies.length} empresas · tres QR permanentes por cliente</p></div><Building2 size={20}/></div>
      <div className="data-table rt-companies-desktop">
        <div className="tr th"><div>Empresa</div><div>CUIT</div><div>Sucursal</div><div>Etiquetas</div><div>Acciones</div></div>
        {companies.map(c => <div className="tr" key={c.id}><div><b>{c.name}</b></div><div>{c.tax_id || "—"}</div><div>{c.site_name || "—"}</div><div><span className="tag"><QrCode size={14}/> 3 QR</span></div><div className="row-actions"><Link className="ghost-btn" href={`/companies/${c.id}/labels`}><Printer size={15}/> Ver / imprimir QR</Link></div></div>)}
      </div>
      <div className="rt-companies-mobile">
        {companies.map(c => <article className="rt-company-mobile-card" key={c.id}>
          <div className="rt-company-mobile-title"><Building2 size={19}/><strong>{c.name}</strong></div>
          <p>CUIT: {c.tax_id || "No informado"} · Sucursal: {c.site_name || "Sin especificar"}</p>
          <div className="rt-company-mobile-meta"><span className="tag"><QrCode size={15}/> 3 QR permanentes</span></div>
          <Link className="primary-btn rt-company-mobile-action" href={`/companies/${c.id}/labels`}><Printer size={18}/> Ver / imprimir 3 QR</Link>
        </article>)}
        {companies.length===0 && <p className="rt-empty-companies">Todavía no hay clientes. Usá Nueva empresa para crear los tres QR iniciales.</p>}
      </div>
    </div>
  </div></AppShell>;
}
