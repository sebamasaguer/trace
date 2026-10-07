"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Building2,
  ClipboardCheck,
  LayoutDashboard,
  LogOut,
  Menu,
  Recycle,
  Route,
  Scale,
  X
} from "lucide-react";
import { clearSession, getSession } from "@/lib/api";

const items = [
  { href: "/dashboard", label: "Resumen", icon: LayoutDashboard },
  { href: "/companies", label: "Empresas y QR", icon: Building2 },
  { href: "/operations", label: "Recolección", icon: Route },
  { href: "/plant", label: "Planta y pesaje", icon: Scale },
  { href: "/reports", label: "Trazabilidad", icon: ClipboardCheck }
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [name, setName] = useState("Usuario");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const session = getSession();
    if (!session.token) router.replace("/login");
    if (session.name) setName(session.name);
  }, [router]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileMenuOpen) return;

    document.body.classList.add("mobile-menu-open");
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileMenuOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.classList.remove("mobile-menu-open");
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [mobileMenuOpen]);

  function logout() {
    setMobileMenuOpen(false);
    clearSession();
    router.push("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Recycle size={22} /></div>
          <div><b>ReciclaTrace</b><span>Trazabilidad inteligente</span></div>
        </div>
        <nav>
          {items.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={pathname.startsWith(href) ? "nav-link active" : "nav-link"}>
              <Icon size={18} /><span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="user-chip"><div className="avatar">{name.charAt(0)}</div><div><b>{name}</b><span>Sesión activa</span></div></div>
          <button className="icon-button" onClick={logout} title="Cerrar sesión"><LogOut size={18} /></button>
        </div>
      </aside>

      <main className="main-area">
        <header className="mobile-top">
          <div className="brand">
            <div className="brand-mark"><Recycle size={20} /></div>
            <div><b>ReciclaTrace</b><span>Trazabilidad inteligente</span></div>
          </div>
          <button
            type="button"
            className="mobile-menu-button"
            aria-label="Abrir menú"
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMobileMenuOpen(true)}
          >
            <Menu size={22} />
          </button>
        </header>

        {children}
      </main>

      <div
        className={mobileMenuOpen ? "mobile-nav-overlay open" : "mobile-nav-overlay"}
        onClick={() => setMobileMenuOpen(false)}
        aria-hidden="true"
      />

      <aside
        id="mobile-navigation"
        className={mobileMenuOpen ? "mobile-drawer open" : "mobile-drawer"}
        aria-hidden={!mobileMenuOpen}
      >
        <div className="mobile-drawer-head">
          <div className="brand">
            <div className="brand-mark"><Recycle size={21} /></div>
            <div><b>ReciclaTrace</b><span>Menú principal</span></div>
          </div>
          <button
            type="button"
            className="mobile-drawer-close"
            aria-label="Cerrar menú"
            onClick={() => setMobileMenuOpen(false)}
          >
            <X size={21} />
          </button>
        </div>

        <nav className="mobile-drawer-nav" aria-label="Navegación principal">
          {items.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={pathname.startsWith(href) ? "mobile-nav-link active" : "mobile-nav-link"}
              onClick={() => setMobileMenuOpen(false)}
            >
              <span className="mobile-nav-icon"><Icon size={19} /></span>
              <span>{label}</span>
            </Link>
          ))}
        </nav>

        <div className="mobile-drawer-foot">
          <div className="mobile-user-card">
            <div className="avatar">{name.charAt(0)}</div>
            <div><b>{name}</b><span>Sesión activa</span></div>
          </div>
          <button type="button" className="mobile-logout" onClick={logout}>
            <LogOut size={18} />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </aside>
    </div>
  );
}
