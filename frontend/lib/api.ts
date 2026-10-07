const CONFIGURED_API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

/**
 * El navegador siempre consume la API por el mismo origen del frontend.
 * Next.js actúa como reverse proxy hacia FastAPI dentro de Docker.
 * Esto evita localhost/IPs hardcodeadas, CORS y permite usar la misma URL HTTPS
 * desde una PC o un celular.
 */
export function getApiUrl() {
  return CONFIGURED_API_URL.replace(/\/$/, "");
}

export const API_URL = CONFIGURED_API_URL;
export type Role = "admin" | "collector" | "plant" | "supervisor";
export type WasteColor = "amarillo" | "verde" | "azul";
export type ScanStage = "pickup" | "plant";

export type Company = {
  id: number;
  name: string;
  tax_id?: string | null;
  site_name?: string | null;
  is_active: boolean;
  created_at: string;
};

export type Label = {
  id: number;
  color: WasteColor;
  material_name: string;
  public_code: string;
  qr_payload: string;
  qr_data_uri: string;
};

export type Trip = {
  id: number;
  route_code: string;
  vehicle: string;
  collector_name: string;
  status: "open" | "arrived" | "closed";
  started_at: string;
  arrived_at?: string | null;
  closed_at?: string | null;
};

export type ManifestRow = {
  company_id: number;
  company_name: string;
  color: WasteColor;
  material_name: string;
  pickup_count: number;
  plant_count: number;
  difference: number;
  weighed_count: number;
  total_kg: string | number;
};

export type Manifest = {
  trip: Trip;
  rows: ManifestRow[];
  pickup_total: number;
  plant_total: number;
  difference_total: number;
  weighed_total: number;
  kg_total: string | number;
};

function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("rt_token");
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${getApiUrl()}${path}`, { ...options, headers, cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || "No se pudo completar la operación");
  return data as T;
}

export function setSession(token: string, role: Role, name: string) {
  localStorage.setItem("rt_token", token);
  localStorage.setItem("rt_role", role);
  localStorage.setItem("rt_name", name);
}

export function clearSession() {
  localStorage.removeItem("rt_token");
  localStorage.removeItem("rt_role");
  localStorage.removeItem("rt_name");
}

export function getSession() {
  if (typeof window === "undefined") return { token: null, role: null, name: null };
  return {
    token: localStorage.getItem("rt_token"),
    role: localStorage.getItem("rt_role") as Role | null,
    name: localStorage.getItem("rt_name")
  };
}

export const colorMeta: Record<WasteColor, { label: string; material: string; className: string }> = {
  amarillo: { label: "Amarillo", material: "Plásticos", className: "yellow" },
  verde: { label: "Verde", material: "Vidrio", className: "green" },
  azul: { label: "Azul", material: "Papel / Cartón", className: "blue" }
};
