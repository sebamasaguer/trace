#!/usr/bin/env python3
"""Carga datos de ejemplo usando la API (respeta todas las reglas de negocio).

Uso:
    python scripts/cargar_datos_demo.py                      # http://localhost:8210
    python scripts/cargar_datos_demo.py --url https://tu-dominio --admin-pass '...'

Es idempotente: si ya existen las empresas/viajes de ejemplo, no los duplica.
Solo usa la librería estándar.
"""
import argparse
import json
import random
import sys
import urllib.error
import urllib.request
import uuid

COMPANIES = [
    ("Supermercados del Sur S.A.", "30-71234567-1", "Sucursal Centro"),
    ("Hotel Plaza Mayor", "30-70987654-3", "Sede Principal"),
    ("Colegio San Martín", "30-68123456-9", "Campus Norte"),
    ("Panificadora La Espiga", "33-70555111-9", "Planta Elaboración"),
]

# (patente, recolector, [(empresa_idx, color, bolsas)], estado_final)
TRIPS = [
    ("DEMO-AB123CD", "Juan Recolector", [(0, "amarillo", 4), (0, "azul", 3), (1, "verde", 3), (2, "azul", 2)], "closed"),
    ("DEMO-EF456GH", "María Gómez", [(1, "amarillo", 3), (3, "azul", 4), (3, "verde", 2)], "partial"),
    ("DEMO-IJ789KL", "Carlos Díaz", [(2, "amarillo", 2), (0, "verde", 3)], "open"),
]


class Api:
    def __init__(self, base):
        self.base = base.rstrip("/") + "/api/v1"
        self.tokens = {}

    def call(self, method, path, body=None, user=None, ok=(200,)):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if user:
            req.add_header("Authorization", "Bearer " + self.tokens[user])
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read() or b"null")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise SystemExit(f"{method} {path} -> {e.code}: {detail}")

    def login(self, role, username, password):
        res = self.call("POST", "/auth/login", {"username": username, "password": password})
        self.tokens[role] = res["access_token"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8210")
    ap.add_argument("--admin-pass", default="Admin123!")
    ap.add_argument("--collector-pass", default="Recolector123!")
    ap.add_argument("--plant-pass", default="Planta123!")
    args = ap.parse_args()

    api = Api(args.url)
    api.login("admin", "admin", args.admin_pass)
    api.login("collector", "recolector", args.collector_pass)
    api.login("plant", "planta", args.plant_pass)
    rng = random.Random(42)

    # Empresas (idempotente por nombre) y sus QR
    existing = {c["name"]: c for c in api.call("GET", "/companies", user="admin")}
    companies = []
    for name, tax, site in COMPANIES:
        c = existing.get(name) or api.call(
            "POST", "/companies", {"name": name, "tax_id": tax, "site_name": site}, user="admin"
        )
        labels = {l["color"]: l["qr_payload"] for l in api.call("GET", f"/companies/{c['id']}/labels", user="admin")}
        companies.append({"id": c["id"], "name": name, "qr": labels})
        print(f"  empresa: {name} ({'existente' if name in existing else 'creada'})")

    done_vehicles = {t["vehicle"] for t in api.call("GET", "/trips", user="admin")}
    for vehicle, collector, bags, final in TRIPS:
        if vehicle in done_vehicles:
            print(f"  viaje {vehicle}: ya existe, se omite")
            continue
        trip = api.call("POST", "/trips", {"vehicle": vehicle, "collector_name": collector}, user="collector")
        tid = trip["id"]
        for idx, color, n in bags:
            for _ in range(n):
                api.call("POST", f"/trips/{tid}/scan", {
                    "qr_payload": companies[idx]["qr"][color], "stage": "pickup",
                    "client_event_id": str(uuid.uuid4()),
                }, user="collector")

        if final in ("closed", "partial"):
            for i, (idx, color, n) in enumerate(bags):
                # En "partial" la última línea queda sin pesar y la anterior a medias.
                to_weigh = n
                if final == "partial" and i == len(bags) - 1:
                    to_weigh = 0
                elif final == "partial" and i == len(bags) - 2:
                    to_weigh = max(1, n - 1)
                for _ in range(to_weigh):
                    api.call("POST", f"/trips/{tid}/weighings", {
                        "qr_payload": companies[idx]["qr"][color], "company_id": companies[idx]["id"],
                        "weight_kg": f"{rng.uniform(2.5, 18.0):.3f}",
                        "client_event_id": str(uuid.uuid4()),
                    }, user="plant")
        if final == "closed":
            api.call("POST", f"/trips/{tid}/close", user="admin")
        print(f"  viaje {trip['route_code']} ({vehicle}): {final}")

    print("Listo.")


if __name__ == "__main__":
    sys.exit(main())
