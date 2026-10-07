"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Leaf, Recycle, ShieldCheck } from "lucide-react";
import { api, Role, setSession } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("Admin123!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const result = await api<{ access_token: string; role: Role; full_name: string }>("/auth/login", {
        method: "POST", body: JSON.stringify({ username, password })
      });
      setSession(result.access_token, result.role, result.full_name);
      router.push("/dashboard");
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo ingresar"); }
    finally { setLoading(false); }
  }

  return <div className="login-page">
    <section className="login-visual">
      <div className="visual-badge"><Leaf size={16}/> Trazabilidad circular</div>
      <div>
        <h1>Del residuo al dato,<br/>sin perder el rastro.</h1>
        <p>QR permanentes por empresa y color, control de recolección, conciliación en planta y pesaje con información en tiempo real.</p>
      </div>
      <div className="visual-metrics"><div><b>3 QR</b><span>por cliente</span></div><div><b>100%</b><span>trazable</span></div><div><b>Tiempo real</b><span>operación y reportes</span></div></div>
    </section>
    <section className="login-panel">
      <form className="login-card" onSubmit={submit}>
        <div className="login-logo"><div className="brand-mark large"><Recycle size={25}/></div><div><b>ReciclaTrace</b><span>Plataforma de gestión</span></div></div>
        <div><h2>Bienvenido</h2><p>Ingresá para administrar la operación.</p></div>
        <label>Usuario<input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username"/></label>
        <label>Contraseña<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password"/></label>
        {error && <div className="alert error">{error}</div>}
        <button className="primary-btn wide" disabled={loading}>{loading ? "Ingresando..." : <>Ingresar <ArrowRight size={18}/></>}</button>
        <div className="demo-box"><ShieldCheck size={17}/><div><b>Acceso demo</b><span>admin / Admin123!</span></div></div>
      </form>
    </section>
  </div>;
}
