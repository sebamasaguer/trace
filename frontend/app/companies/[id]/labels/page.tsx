"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Printer, Recycle } from "lucide-react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { api, Company, Label, colorMeta } from "@/lib/api";

export default function LabelsPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [labels, setLabels] = useState<Label[]>([]);
  const [company, setCompany] = useState<Company | null>(null);
  useEffect(() => { api<Company[]>("/companies").then(all => setCompany(all.find(x => x.id === id) || null)); api<Label[]>(`/companies/${id}/labels`).then(setLabels); }, [id]);
  return <AppShell><div className="page-wrap print-page">
    <div className="page-header no-print"><div><Link className="back-link" href="/companies"><ArrowLeft size={16}/> Empresas</Link><h1>Etiquetas QR</h1><p>Imprimí tantas copias de cada color como necesite el cliente.</p></div><button className="primary-btn" onClick={() => window.print()}><Printer size={17}/> Imprimir etiquetas</button></div>
    <div className="label-title print-only"><Recycle size={24}/><b>ReciclaTrace · Etiquetas del cliente</b></div>
    <div className="label-grid">
      {labels.map(label => { const meta = colorMeta[label.color]; return <div className={`qr-label ${meta.className}`} key={label.id}><div className="qr-color-band">{meta.label.toUpperCase()}</div><div className="qr-company"><span>EMPRESA</span><h2>{company?.name || "Cliente"}</h2><p>{company?.site_name || ""}</p></div><img src={label.qr_data_uri} alt={`QR ${meta.label}`}/><div className="qr-data"><b>{label.material_name}</b><span>{label.public_code}</span><small>Escanear una vez por cada bolsa</small></div></div>; })}
    </div>
    <div className="rt-labels-mobile-print no-print"><button className="primary-btn wide" type="button" onClick={() => window.print()}><Printer size={18}/> Imprimir o guardar como PDF</button><p>Las tres etiquetas son permanentes. Imprimí las copias que necesites; no generes códigos nuevos para cada bolsa.</p></div>
  </div></AppShell>;
}
