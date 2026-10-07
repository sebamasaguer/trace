from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, companies, dashboard, trips

app = FastAPI(
    title=settings.app_name,
    version="0.1.5-demo",
    description="Trazabilidad de reciclaje por QR, recepción y pesaje.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": "0.1.5-demo"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(companies.router, prefix=settings.api_prefix)
app.include_router(trips.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
