import os
import json
import asyncio
import logging
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import motor.motor_asyncio
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = os.getenv("DB_NAME", "raspi_db")
API_KEY = os.getenv("API_KEY", "MACMECMIC")

logging.info(f"Connecting to MongoDB at {MONGO_URI}, DB: {DB_NAME}")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="./static"), name="static")
templates = Jinja2Templates(directory="./templates")

# Simple in-memory websocket manager
class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active[device_id] = websocket

    def disconnect(self, device_id: str):
        self.active.pop(device_id, None)

    async def send_json(self, device_id: str, data: Any):
        ws = self.active.get(device_id)
        if ws:
            await ws.send_json(data)
            return True
        return False

manager = ConnectionManager()

# Pydantic models
class DeviceCreate(BaseModel):
    name: str
    vehicle_id: str | None = None
    meta: dict = Field(default_factory=dict)

class DeviceOut(DeviceCreate):
    id: str
    online: bool = False

class CommandCreate(BaseModel):
    device_id: str
    action: str
    relay: int = 0

# Helpers
def oid_str(o):
    return str(o)

async def device_by_id(device_id: str):
    try:
        if not ObjectId.is_valid(device_id):
            return None
        doc = await db.devices.find_one({"_id": ObjectId(device_id)})
    except Exception:
        return None
    if not doc:
        return None
    doc["id"] = oid_str(doc["_id"])
    doc.pop("_id", None)
    doc.setdefault("online", False)
    return doc

# Web UI
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# API: devices
@app.get("/api/ping/{device_id}")
async def ping_device(device_id: str):
    d = await device_by_id(device_id)
    if not d:
        raise HTTPException(status_code=404, detail="device not found")
    return {"online": device_id in manager.active}

@app.get("/api/devices")
async def list_devices():
    docs = []
    cursor = db.devices.find({})
    async for d in cursor:
        d["id"] = oid_str(d["_id"])
        d.pop("_id", None)
        d.setdefault("online", d["id"] in manager.active)
        docs.append(d)
    return docs

@app.post("/api/devices")
async def create_device(device: DeviceCreate):
    doc = device.dict()
    res = await db.devices.insert_one(doc)
    return {"id": oid_str(res.inserted_id), **doc}

@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    d = await device_by_id(device_id)
    if not d:
        raise HTTPException(status_code=404, detail="device not found")
    d["online"] = device_id in manager.active
    return d

class DeviceUpdate(BaseModel):
    name: str | None = None
    vehicle_id: str | None = None
    meta: dict | None = None

@app.put("/api/devices/{device_id}")
async def update_device(device_id: str, update_data: DeviceUpdate):
    if not ObjectId.is_valid(device_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Filtrar solo campos que no sean None
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No data to update")

    res = await db.devices.update_one(
        {"_id": ObjectId(device_id)},
        {"$set": update_dict}
    )
    
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"result": "updated", "fields": list(update_dict.keys())}

@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str):
    res = await db.devices.delete_one({"_id": ObjectId(device_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="device not found")
    await db.commands.delete_many({"device_id": device_id})
    return {"result": "deleted"}

# API: send command
@app.post("/api/command")
async def send_command(cmd: CommandCreate, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        logging.warning("Unauthorized attempt to send command")
        raise HTTPException(status_code=401, detail="Invalid API key")
    # Validación estricta de campos
    if not cmd.device_id or not cmd.action or cmd.relay not in [0, 1]:
        logging.warning(f"Invalid command data: {cmd}")
        raise HTTPException(status_code=422, detail="Invalid command data")
    cmd_doc = cmd.dict()
    cmd_doc["status"] = "pending"
    # Asegurar que el device_id sea un string para el manager
    target_id = str(cmd.device_id)
    
    await db.commands.insert_one(cmd_doc)
    
    # IMPORTANTE: MongoDB añade un '_id' que es un ObjectId y NO es serializable a JSON.
    # Debemos convertirlo a string antes de enviarlo por el WebSocket.
    if "_id" in cmd_doc:
        cmd_doc["id"] = str(cmd_doc["_id"])
        del cmd_doc["_id"]

    sent = await manager.send_json(target_id, {"type": "command", "payload": cmd_doc})
    if sent:
        await db.commands.update_many({"device_id": cmd.device_id, "status": "pending"}, {"$set": {"status": "sent"}})
        logging.info(f"Command sent: {cmd_doc}")
        return {"result": "sent"}
    logging.info(f"Command queued: {cmd_doc}")
    return {"result": "queued"}

# WebSocket for agents
@app.websocket("/ws/{device_id}")
async def device_ws(websocket: WebSocket, device_id: str):
    logging.info(f"Intento de conexión desde: {device_id}")
    
    # Intentar buscar por ID o por Nombre
    query = {"$or": [{"name": device_id}]}
    if ObjectId.is_valid(device_id):
        query["$or"].append({"_id": ObjectId(device_id)})
    
    device = await db.devices.find_one(query)

    if not device:
        logging.info(f"No se encontró el dispositivo {device_id}. Creando uno nuevo...")
        new_doc = {
            "name": device_id, 
            "vehicle_id": "AUTO-" + device_id[:4], 
            "online": True,
            "meta": {"status": "initialized"}
        }
        res = await db.devices.insert_one(new_doc)
        real_id = str(res.inserted_id)
    else:
        real_id = str(device["_id"])
        logging.info(f"Dispositivo encontrado: {device['name']} con ID {real_id}")

    # Aceptar conexión ANTES de marcar en DB para evitar bloqueos
    await manager.connect(real_id, websocket)
    
    # Actualizar estado a online
    await db.devices.update_one({"_id": ObjectId(real_id)}, {"$set": {"online": True}})
    
    try:
        while True:
            data = await websocket.receive_json()
            typ = data.get("type")
            if typ == "status":
                meta = data.get("meta", {})
                # 1. Actualizar la colección de dispositivos (para el dashboard)
                await db.devices.update_one({"_id": ObjectId(real_id)}, {"$set": {"meta": meta}})
                
                # 2. Sincronizar con vehicle_locations para la base de datos externa
                # Obtenemos la matrícula actual del dispositivo
                current_dev = await db.devices.find_one({"_id": ObjectId(real_id)})
                plate = current_dev.get("license_plate") or current_dev.get("vehicle_id")
                
                if plate:
                    sensors = meta.get("sensors", {})
                    gps = sensors.get("gps", {})
                    relays = meta.get("relays", {})
                    
                    # El vehículo está 'active' si el Relay 0 está ON
                    is_active = relays.get("0", False)
                    
                    location_doc = {
                        "license_plate": plate,
                        "latitude": gps.get("lat", 0.0),
                        "longitude": gps.get("lon", 0.0),
                        "speed": gps.get("speed", 0.0),
                        "engine_temp": sensors.get("engine", {}).get("temp", 0.0),
                        "rpm": sensors.get("engine", {}).get("rpm", 0),
                        "battery_voltage": sensors.get("battery", 0.0),
                        "active": is_active,
                        "last_update": asyncio.get_event_loop().time()
                    }
                    
                    # Upsert en vehicle_locations usando license_plate como clave
                    await db.vehicle_locations.update_one(
                        {"license_plate": plate},
                        {"$set": location_doc},
                        upsert=True
                    )
                    logging.debug(f"Sincronizado vehicle_locations para {plate}")

            elif typ == "ack":
                await db.commands.update_one({"device_id": real_id, "status": "sent"}, {"$set": {"status": "ack"}})
    except WebSocketDisconnect:
        manager.disconnect(real_id)
        await db.devices.update_one({"_id": ObjectId(real_id)}, {"$set": {"online": False}})
    except Exception as e:
        logging.error(f"Error en WS {real_id}: {e}")
        manager.disconnect(real_id)
        await db.devices.update_one({"_id": ObjectId(real_id)}, {"$set": {"online": False}})

# Simple health
@app.get("/health")
async def health():
    try:
        await client.admin.command("ping")
        return {"ok": True}
    except Exception:
        return {"ok": False}
