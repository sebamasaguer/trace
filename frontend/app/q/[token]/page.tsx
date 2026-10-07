"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckCircle2, Recycle } from "lucide-react";
import { getApiUrl, colorMeta, WasteColor } from "@/lib/api";

type Verify = { company_name:string; color:WasteColor; material_name:string; public_code:string };
export default function PublicQrPage(){
 const p=useParams<{token:string}>(); const [data,setData]=useState<Verify|null>(null); const [error,setError]=useState("");
 useEffect(()=>{const payload=`${window.location.origin}/q/${p.token}`;fetch(`${getApiUrl()}/companies/verify/label?payload=${encodeURIComponent(payload)}`).then(async r=>{const j=await r.json();if(!r.ok)throw new Error(j.detail||"QR inválido");setData(j)}).catch(e=>setError(e.message));},[p.token]);
 return <div className="public-qr"><div className="public-card"><div className="login-logo"><div className="brand-mark large"><Recycle size={25}/></div><div><b>ReciclaTrace</b><span>Verificación de etiqueta</span></div></div>{error&&<div className="alert error">{error}</div>}{data&&<><CheckCircle2 size={42}/><h1>Etiqueta válida</h1><p>Este QR pertenece a:</p><h2>{data.company_name}</h2><div className={`public-color ${colorMeta[data.color].className}`}>{colorMeta[data.color].label} · {data.material_name}</div><small>{data.public_code}</small></>}</div></div>
}
