import { LucideIcon } from "lucide-react";

export default function KpiCard({ label, value, sub, icon: Icon }: { label: string; value: string | number; sub?: string; icon: LucideIcon }) {
  return <div className="kpi-card"><div className="kpi-head"><span>{label}</span><div className="kpi-icon"><Icon size={18}/></div></div><strong>{value}</strong>{sub && <small>{sub}</small>}</div>;
}
