import base64, hmac, os, time
from hashlib import sha256
from pathlib import Path
import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Customer, Delivery, Deposit, RoutePlan, Vehicle
from .optimizer import optimize_route
from .schemas import CustomerIn, DepositIn, RoutePlanIn, VehicleIn

APP_USER = os.getenv("APP_USER", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "admin123")
APP_SECRET = os.getenv("APP_SECRET", "dev-secret-change-me")

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Tool Consegne Aziendale V3.3")
static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

def sign(value):
    return hmac.new(APP_SECRET.encode(), value.encode(), sha256).hexdigest()

def make_token(username):
    raw = f"{username}:{int(time.time())}"
    token = base64.urlsafe_b64encode(raw.encode()).decode()
    return f"{token}.{sign(token)}"

def verify_token(token):
    if not token or "." not in token: return False
    body, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, sign(body)): return False
    try:
        raw = base64.urlsafe_b64decode(body.encode()).decode()
        username, ts = raw.split(":")
        return username == APP_USER and int(time.time()) - int(ts) < 60*60*24*7
    except Exception:
        return False

def require_auth(request: Request):
    if not verify_token(request.cookies.get("session")):
        raise HTTPException(status_code=401, detail="Non autenticato")

@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")

@app.post("/api/login")
async def login(payload: dict, response: Response):
    if payload.get("username") == APP_USER and payload.get("password") == APP_PASSWORD:
        response.set_cookie("session", make_token(APP_USER), httponly=True, samesite="lax", max_age=60*60*24*7)
        return {"ok": True}
    raise HTTPException(401, "Credenziali errate")

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}

@app.get("/api/me")
def me(request: Request):
    return {"authenticated": verify_token(request.cookies.get("session")), "username": APP_USER}

@app.get("/api/deposits")
def list_deposits(db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(Deposit).order_by(Deposit.predefinito.desc(), Deposit.nome.asc()).all()

@app.post("/api/deposits")
def create_deposit(data: DepositIn, db: Session = Depends(get_db), _=Depends(require_auth)):
    if data.predefinito: db.query(Deposit).update({"predefinito": False})
    item = Deposit(**data.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item

@app.put("/api/deposits/{item_id}")
def update_deposit(item_id: int, data: DepositIn, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = db.get(Deposit, item_id)
    if not item: raise HTTPException(404, "Deposito non trovato")
    if data.predefinito: db.query(Deposit).filter(Deposit.id != item_id).update({"predefinito": False})
    for k,v in data.model_dump().items(): setattr(item,k,v)
    db.commit(); db.refresh(item)
    return item

@app.delete("/api/deposits/{item_id}")
def delete_deposit(item_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = db.get(Deposit, item_id)
    if not item: raise HTTPException(404, "Deposito non trovato")
    db.delete(item); db.commit()
    return {"ok": True}

@app.get("/api/customers")
def list_customers(q: str = "", db: Session = Depends(get_db), _=Depends(require_auth)):
    query = db.query(Customer)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Customer.nome.ilike(like), Customer.codice_cliente.ilike(like), Customer.indirizzo.ilike(like)))
    return query.order_by(Customer.nome.asc()).limit(300).all()

@app.post("/api/customers")
def create_customer(data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = Customer(**data.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item

@app.put("/api/customers/{item_id}")
def update_customer(item_id: int, data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = db.get(Customer, item_id)
    if not item: raise HTTPException(404, "Cliente non trovato")
    for k,v in data.model_dump().items(): setattr(item,k,v)
    db.commit(); db.refresh(item)
    return item

@app.delete("/api/customers/{item_id}")
def delete_customer(item_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = db.get(Customer, item_id)
    if not item: raise HTTPException(404, "Cliente non trovato")
    db.delete(item); db.commit()
    return {"ok": True}

@app.post("/api/customers/import")
async def import_customers(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(require_auth)):
    name = file.filename or "import"
    content = await file.read()
    tmp = Path("/tmp") / name
    tmp.write_bytes(content)
    df = pd.read_csv(tmp) if name.lower().endswith(".csv") else pd.read_excel(tmp)
    created, updated = 0, 0
    def get(row, col, default=None):
        if col not in row or pd.isna(row[col]): return default
        return row[col]
    def b(x):
        return str(x).strip().lower() in ["1", "si", "sì", "yes", "true", "vero"]
    for _, row in df.iterrows():
        codice = str(get(row, "codice_cliente", "") or "").strip()
        nome = str(get(row, "nome", "") or "").strip()
        indirizzo = str(get(row, "indirizzo", "") or "").strip()
        if not nome or not indirizzo: continue
        item = db.query(Customer).filter(Customer.codice_cliente == codice).first() if codice else None
        if not item:
            item = Customer(); db.add(item); created += 1
        else:
            updated += 1
        item.codice_cliente = codice or None
        item.nome = nome
        item.indirizzo = indirizzo
        item.comune = get(row, "comune")
        item.provincia = get(row, "provincia")
        item.telefono = str(get(row, "telefono", "") or "")
        item.referente = get(row, "referente")
        item.email = get(row, "email")
        item.scarico_mattina_da = get(row, "scarico_mattina_da")
        item.scarico_mattina_a = get(row, "scarico_mattina_a")
        item.scarico_pomeriggio_da = get(row, "scarico_pomeriggio_da")
        item.scarico_pomeriggio_a = get(row, "scarico_pomeriggio_a")
        item.tempo_scarico_min = int(get(row, "tempo_scarico_min", 10) or 10)
        item.ztl = b(get(row, "ztl", False))
        item.sponda = b(get(row, "sponda", False))
        item.transpallet = b(get(row, "transpallet", False))
        item.note = get(row, "note")
    db.commit()
    return {"created": created, "updated": updated}

@app.get("/api/vehicles")
def list_vehicles(db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(Vehicle).order_by(Vehicle.nome.asc()).all()

@app.post("/api/vehicles")
def create_vehicle(data: VehicleIn, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = Vehicle(**data.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item

@app.put("/api/vehicles/{item_id}")
def update_vehicle(item_id: int, data: VehicleIn, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = db.get(Vehicle, item_id)
    if not item: raise HTTPException(404, "Mezzo non trovato")
    for k,v in data.model_dump().items(): setattr(item,k,v)
    db.commit(); db.refresh(item)
    return item

@app.delete("/api/vehicles/{item_id}")
def delete_vehicle(item_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    item = db.get(Vehicle, item_id)
    if not item: raise HTTPException(404, "Mezzo non trovato")
    db.delete(item); db.commit()
    return {"ok": True}

@app.post("/api/routes/optimize")
def create_and_optimize_route(data: RoutePlanIn, db: Session = Depends(get_db), _=Depends(require_auth)):
    deposit = db.get(Deposit, data.deposit_id)
    if not deposit: raise HTTPException(400, "Deposito non trovato")
    vehicle = db.get(Vehicle, data.vehicle_id) if data.vehicle_id else None
    vehicle_dict = None
    if vehicle: vehicle_dict = {"ha_sponda": vehicle.ha_sponda, "accesso_ztl": vehicle.accesso_ztl}
    deliveries = [c.model_dump() for c in data.consegne]
    result = optimize_route(deposit.indirizzo, deliveries, vehicle_dict, data.rientro_deposito, data.orario_partenza)
    consumo = vehicle.consumo_l_100km if vehicle else 8.5
    litri = result["total_km"] * consumo / 100
    costo_carburante = litri * data.prezzo_carburante_litro
    plan = RoutePlan(
        nome=data.nome, data_giro=data.data_giro, orario_partenza=data.orario_partenza,
        orario_rientro_stimato=result["return_time"],
        deposit_id=data.deposit_id, vehicle_id=data.vehicle_id, rientro_deposito=data.rientro_deposito,
        prezzo_carburante_litro=data.prezzo_carburante_litro,
        totale_km=result["total_km"], totale_minuti=result["total_min"],
        litri_stimati=round(litri,2), costo_carburante=round(costo_carburante,2),
        costo_totale=round(costo_carburante,2), google_maps_url=result["google_maps_url"]
    )
    db.add(plan); db.flush()
    for item in result["ordered"]:
        item.pop("coord", None)
        db.add(Delivery(route_plan_id=plan.id, **item))
    db.commit(); db.refresh(plan)
    return {
        "id": plan.id, "nome": plan.nome, "data_giro": plan.data_giro,
        "orario_partenza": plan.orario_partenza, "orario_rientro_stimato": plan.orario_rientro_stimato,
        "totale_km": plan.totale_km, "totale_minuti": plan.totale_minuti,
        "litri_stimati": plan.litri_stimati, "costo_carburante": plan.costo_carburante,
        "costo_totale": plan.costo_totale, "google_maps_url": plan.google_maps_url,
        "consegne": result["ordered"]
    }


def serialize_route(plan):
    consegne = sorted(plan.deliveries, key=lambda x: x.ordine or 0)
    return {
        "id": plan.id,
        "nome": plan.nome,
        "data_giro": plan.data_giro,
        "orario_partenza": plan.orario_partenza,
        "orario_rientro_stimato": plan.orario_rientro_stimato,
        "deposit_id": plan.deposit_id,
        "vehicle_id": plan.vehicle_id,
        "rientro_deposito": plan.rientro_deposito,
        "prezzo_carburante_litro": plan.prezzo_carburante_litro,
        "totale_km": plan.totale_km,
        "totale_minuti": plan.totale_minuti,
        "litri_stimati": plan.litri_stimati,
        "costo_carburante": plan.costo_carburante,
        "costo_totale": plan.costo_totale,
        "google_maps_url": plan.google_maps_url,
        "consegne": [
            {
                "id": d.id,
                "customer_id": d.customer_id,
                "cliente_nome": d.cliente_nome,
                "indirizzo": d.indirizzo,
                "peso_kg": d.peso_kg,
                "colli": d.colli,
                "scarico_mattina_da": d.scarico_mattina_da,
                "scarico_mattina_a": d.scarico_mattina_a,
                "scarico_pomeriggio_da": d.scarico_pomeriggio_da,
                "scarico_pomeriggio_a": d.scarico_pomeriggio_a,
                "tempo_scarico_min": d.tempo_scarico_min,
                "ztl": d.ztl,
                "sponda": d.sponda,
                "note": d.note,
                "ordine": d.ordine,
                "km_tappa": d.km_tappa,
                "minuti_tappa": d.minuti_tappa,
                "arrivo_stimato": d.arrivo_stimato,
                "partenza_stimata": d.partenza_stimata,
                "attesa_min": d.attesa_min,
                "warning": d.warning,
            }
            for d in consegne
        ],
    }

@app.get("/api/routes/{route_id}")
def get_route(route_id: int, db: Session = Depends(get_db), _=Depends(require_auth)):
    plan = db.get(RoutePlan, route_id)
    if not plan:
        raise HTTPException(404, "Giro non trovato")
    return serialize_route(plan)

@app.get("/api/routes")
def list_routes(db: Session = Depends(get_db), _=Depends(require_auth)):
    return db.query(RoutePlan).order_by(RoutePlan.created_at.desc()).limit(100).all()
