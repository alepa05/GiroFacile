from pydantic import BaseModel
from typing import Optional, List

class DepositIn(BaseModel):
    nome: str
    indirizzo: str
    predefinito: bool = False
    note: Optional[str] = None

class CustomerIn(BaseModel):
    codice_cliente: Optional[str] = None
    nome: str
    indirizzo: str
    comune: Optional[str] = None
    provincia: Optional[str] = None
    telefono: Optional[str] = None
    referente: Optional[str] = None
    email: Optional[str] = None
    scarico_mattina_da: Optional[str] = None
    scarico_mattina_a: Optional[str] = None
    scarico_pomeriggio_da: Optional[str] = None
    scarico_pomeriggio_a: Optional[str] = None
    tempo_scarico_min: int = 10
    ztl: bool = False
    sponda: bool = False
    transpallet: bool = False
    note: Optional[str] = None

class VehicleIn(BaseModel):
    nome: str
    targa: Optional[str] = None
    consumo_l_100km: float = 8.5
    capacita_kg: float = 1000
    capacita_colli: int = 100
    ha_sponda: bool = False
    accesso_ztl: bool = False
    note: Optional[str] = None

class DeliveryIn(BaseModel):
    customer_id: Optional[int] = None
    cliente_nome: str
    indirizzo: str
    peso_kg: float = 0
    colli: int = 0
    scarico_mattina_da: Optional[str] = None
    scarico_mattina_a: Optional[str] = None
    scarico_pomeriggio_da: Optional[str] = None
    scarico_pomeriggio_a: Optional[str] = None
    tempo_scarico_min: int = 10
    ztl: bool = False
    sponda: bool = False
    note: Optional[str] = None

class RoutePlanIn(BaseModel):
    nome: str
    data_giro: str
    orario_partenza: str = "08:00"
    deposit_id: int
    vehicle_id: Optional[int] = None
    rientro_deposito: bool = True
    prezzo_carburante_litro: float = 1.75
    consegne: List[DeliveryIn]
