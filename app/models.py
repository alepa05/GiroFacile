from sqlalchemy import Boolean, Float, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .database import Base

class Deposit(Base):
    __tablename__ = "deposits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    indirizzo: Mapped[str] = mapped_column(String(500), nullable=False)
    predefinito: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codice_cliente: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    nome: Mapped[str] = mapped_column(String(250), index=True, nullable=False)
    indirizzo: Mapped[str] = mapped_column(String(500), nullable=False)
    comune: Mapped[str | None] = mapped_column(String(150), nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referente: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scarico_mattina_da: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scarico_mattina_a: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scarico_pomeriggio_da: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scarico_pomeriggio_a: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tempo_scarico_min: Mapped[int] = mapped_column(Integer, default=10)
    ztl: Mapped[bool] = mapped_column(Boolean, default=False)
    sponda: Mapped[bool] = mapped_column(Boolean, default=False)
    transpallet: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    targa: Mapped[str | None] = mapped_column(String(50), nullable=True)
    consumo_l_100km: Mapped[float] = mapped_column(Float, default=8.5)
    capacita_kg: Mapped[float] = mapped_column(Float, default=1000)
    capacita_colli: Mapped[int] = mapped_column(Integer, default=100)
    ha_sponda: Mapped[bool] = mapped_column(Boolean, default=False)
    accesso_ztl: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

class RoutePlan(Base):
    __tablename__ = "route_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(250), nullable=False)
    data_giro: Mapped[str] = mapped_column(String(20), nullable=False)
    orario_partenza: Mapped[str] = mapped_column(String(10), default="08:00")
    orario_rientro_stimato: Mapped[str | None] = mapped_column(String(10), nullable=True)
    deposit_id: Mapped[int | None] = mapped_column(ForeignKey("deposits.id"), nullable=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    rientro_deposito: Mapped[bool] = mapped_column(Boolean, default=True)
    prezzo_carburante_litro: Mapped[float] = mapped_column(Float, default=1.75)
    totale_km: Mapped[float] = mapped_column(Float, default=0)
    totale_minuti: Mapped[float] = mapped_column(Float, default=0)
    litri_stimati: Mapped[float] = mapped_column(Float, default=0)
    costo_carburante: Mapped[float] = mapped_column(Float, default=0)
    costo_totale: Mapped[float] = mapped_column(Float, default=0)
    google_maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    deposit = relationship("Deposit")
    vehicle = relationship("Vehicle")
    deliveries = relationship("Delivery", cascade="all, delete-orphan")

class Delivery(Base):
    __tablename__ = "deliveries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    route_plan_id: Mapped[int] = mapped_column(ForeignKey("route_plans.id"), nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    cliente_nome: Mapped[str] = mapped_column(String(250), nullable=False)
    indirizzo: Mapped[str] = mapped_column(String(500), nullable=False)
    peso_kg: Mapped[float] = mapped_column(Float, default=0)
    colli: Mapped[int] = mapped_column(Integer, default=0)
    scarico_mattina_da: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scarico_mattina_a: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scarico_pomeriggio_da: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scarico_pomeriggio_a: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tempo_scarico_min: Mapped[int] = mapped_column(Integer, default=10)
    ztl: Mapped[bool] = mapped_column(Boolean, default=False)
    sponda: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordine: Mapped[int] = mapped_column(Integer, default=0)
    km_tappa: Mapped[float] = mapped_column(Float, default=0)
    minuti_tappa: Mapped[float] = mapped_column(Float, default=0)
    arrivo_stimato: Mapped[str | None] = mapped_column(String(10), nullable=True)
    partenza_stimata: Mapped[str | None] = mapped_column(String(10), nullable=True)
    attesa_min: Mapped[float] = mapped_column(Float, default=0)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer = relationship("Customer")
