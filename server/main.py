import os
import json
import asyncio
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import motor.motor_asyncio
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

MONGO_URI = os.getenv("MONGO_URI", os.getenv("MONGODB_URI", "mongodb://mongo:27017"))
DB_NAME = os.getenv("DB_NAME", os.getenv("MONGODB_DATABASE", "raspi_db"))
API_KEY = os.getenv("IOT_API_KEY", os.getenv("API_KEY", "MACMECMIC"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.info(f"Connecting to MongoDB at {MONGO_URI}, DB: {DB_NAME}")

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

# Simple in-memory websocket manager
class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
        self.hardware_to_id: Dict[str, str] = {}

    async def connect(self, device_id: str, hardware_id: str, websocket: WebSocket):
        self.active[device_id] = websocket
        self.hardware_to_id[hardware_id] = device_id

    def disconnect(self, device_id: str):
        self.active.pop(device_id, None)
        # Limpiar hardware_to_id (reverso)
        self.hardware_to_id = {k: v for k, v in self.hardware_to_id.items() if v != device_id}

    def is_online(self, device_id: str = None, hardware_id: str = None) -> bool:
        # Check by device_id (exact match in active sessions)
        if device_id and device_id in self.active:
            return True
            
        # Check by hardware_id (lookup in our hardware map)
        if hardware_id:
            hid = self.hardware_to_id.get(hardware_id)
            if hid and hid in self.active:
                return True
                
        return False

    async def send_json(self, device_id: str, data: Any):
        ws = self.active.get(device_id)
        if ws:
            try:
                await ws.send_json(data)
                return True
            except:
                self.disconnect(device_id)
        return False

manager = ConnectionManager()

# Authentication dependency
async def verify_token(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Pydantic models
class CommandCreate(BaseModel):
    device_id: str
    action: str
    relay: int = 0

class DeviceUpdate(BaseModel):
    license_plate: str
    name: str = None

# API: global devices for central admin
@app.get("/api/central/devices")
async def list_all_devices(only_online: bool = False, token: str = Header(None, alias="x-api-key")):
    try:
        logging.info(f"SuperAdmin request received with token: {token[:3] if token else 'None'}... (Only Online: {only_online})")
        await verify_token(token)
        
        docs = []
        db_hardware_ids = set()
        
        # 1. Obtener dispositivos de la DB
        cursor = db.vehicle_locations.find({})
        async for d in cursor:
            id_str = str(d["_id"])
            hw_id = d.get("identity", {}).get("hardware_id")
            if hw_id:
                db_hardware_ids.add(hw_id)
            
            is_online = manager.is_online(device_id=id_str, hardware_id=hw_id)
            
            if only_online and not is_online:
                continue
                
            identity = d.get("identity", {})
            docs.append({
                "id": id_str,
                "tenant_id": d.get("tenant_id", "unknown"),
                "name": identity.get("name", "Unknown"),
                "hardware_id": hw_id or "S/N",
                "ip_address": d.get("status", {}).get("ip_address", "Unknown"),
                "online": is_online,
                "active": d.get("status", {}).get("active", False)
            })
        
        # 2. Añadir dispositivos que están en memoria (WS) pero NO en la lista de la DB anterior
        for hw_id, device_id in manager.hardware_to_id.items():
            if hw_id not in db_hardware_ids:
                docs.append({
                    "id": device_id,
                    "tenant_id": "WS_ONLY",
                    "name": "Dispositivo Volátil",
                    "hardware_id": hw_id,
                    "ip_address": "Unknown",
                    "online": True
                })
        
        logging.info(f"Total devices returned: {len(docs)}. Active WebSockets: {len(manager.active)}")
        return docs
    except Exception as e:
        logging.error(f"Error in list_all_devices: {str(e)}")
        return {"error": str(e), "trace": "Check server logs"}

# API: devices
@app.get("/api/{tenant_id}/devices")
async def list_devices(tenant_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    docs = []
    cursor = db.vehicle_locations.find({"tenant_id": tenant_id})
    async for d in cursor:
        id_str = str(d["_id"])
        docs.append({
            "id": id_str,
            "name": d.get("identity", {}).get("name", "Unknown"),
            "hardware_id": d.get("identity", {}).get("hardware_id", "Unknown"),
            "license_plate": d.get("identity", {}).get("license_plate", "Unknown"),
            "online": id_str in manager.active,
            "meta": d.get("meta", {}),
            "telemetry": d.get("telemetry", {}),
            "status": d.get("status", {})
        })
    return docs

@app.get("/api/{tenant_id}/devices/{device_id}")
async def get_device(tenant_id: str, device_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
        
    device = await db.vehicle_locations.find_one({"_id": obj_id, "tenant_id": tenant_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    id_str = str(device["_id"])
    return {
        "id": id_str,
        "name": device["identity"]["name"],
        "hardware_id": device["identity"]["hardware_id"],
        "license_plate": device["identity"]["license_plate"],
        "online": id_str in manager.active,
        "meta": device.get("meta", {}),
        "telemetry": device.get("telemetry", {}),
        "status": device.get("status", {})
    }

@app.put("/api/{tenant_id}/devices/{device_id}")
async def update_device(tenant_id: str, device_id: str, update: DeviceUpdate, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
        
    # Prepare update data
    update_data = {"identity.license_plate": update.license_plate}
    if update.name:
        update_data["identity.name"] = update.name
        
    result = await db.vehicle_locations.update_one(
        {"_id": obj_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
        
    return {"status": "updated"}

@app.delete("/api/{tenant_id}/devices/{device_id}")
async def delete_device(tenant_id: str, device_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
        
    # Check if device exists to get its ID for websocket cleanup
    device = await db.vehicle_locations.find_one({"_id": obj_id, "tenant_id": tenant_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    # Delete from MongoDB
    await db.vehicle_locations.delete_one({"_id": obj_id, "tenant_id": tenant_id})
    
    # Close websocket if active to prevent immediate re-creation via WS loop
    if device_id in manager.active:
        ws = manager.active[device_id]
        try:
            await ws.close(code=1000, reason="Device deleted from system")
        except:
            pass
        manager.disconnect(device_id)
        
    return {"status": "deleted"}

@app.get("/api/{tenant_id}/ping/{device_id}")
async def ping_device(tenant_id: str, device_id: str):
    # Verify device belongs to tenant
    try:
        obj_id = ObjectId(device_id)
    except:
        return {"device_id": device_id, "online": False, "error": "Invalid ID"}
        
    device = await db.vehicle_locations.find_one({"_id": obj_id, "tenant_id": tenant_id})
    if not device:
        return {"device_id": device_id, "online": False, "error": "Device not found for this tenant"}
        
    return {"device_id": device_id, "online": device_id in manager.active}

@app.get("/api/{tenant_id}/devices/{device_id}/route")
async def get_device_route(tenant_id: str, device_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
    
    device = await db.vehicle_locations.find_one({"_id": obj_id, "tenant_id": tenant_id}, {"route": 1})
    if not device:
        return []
    return device.get("route", [])

@app.post("/api/{tenant_id}/devices/{device_id}/route/clear")
async def clear_device_route(tenant_id: str, device_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
        
    await db.vehicle_locations.update_one({"_id": obj_id, "tenant_id": tenant_id}, {"$set": {"route": []}})
    return {"status": "cleared"}

# API: send command
@app.post("/api/{tenant_id}/command")
async def send_command(tenant_id: str, cmd: CommandCreate, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    
    # Verify device belongs to tenant
    try:
        obj_id = ObjectId(cmd.device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
        
    device = await db.vehicle_locations.find_one({"_id": obj_id, "tenant_id": tenant_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found for this tenant")

    cmd_doc = cmd.dict()
    cmd_doc["tenant_id"] = tenant_id
    cmd_doc["status"] = "pending"
    cmd_doc["created_at"] = datetime.now().isoformat()
    target_id = str(cmd.device_id)
    
    await db.commands.insert_one(cmd_doc)
    if "_id" in cmd_doc:
        cmd_doc["id"] = str(cmd_doc["_id"])
        del cmd_doc["_id"]

    sent = await manager.send_json(target_id, {"type": "command", "payload": cmd_doc})
    if sent:
        await db.commands.update_many({"device_id": cmd.device_id, "status": "pending", "tenant_id": tenant_id}, {"$set": {"status": "sent"}})
        return {"result": "sent"}
    return {"result": "queued"}

# WebSocket for agents
@app.websocket("/ws/{tenant_id}/{hardware_id}")
async def device_ws(websocket: WebSocket, tenant_id: str, hardware_id: str, token: str = None):
    # Verify token
    if token != API_KEY:
        await websocket.close(code=1008, reason="Invalid API Key")
        return

    await websocket.accept()
    client_ip = websocket.client.host

    # Buscar si ya existe
    device = await db.vehicle_locations.find_one({
        "identity.hardware_id": hardware_id,
        "tenant_id": tenant_id
    })

    if device:
        real_id = str(device["_id"])
    else:
        new_doc = {
            "tenant_id": tenant_id,
            "identity": {
                "hardware_id": hardware_id, 
                "name": hardware_id, 
                "license_plate": "AUTO-" + hardware_id[-4:]
            },
            "status": {"online": True, "active": False, "last_update": datetime.now().timestamp(), "ip_address": client_ip},
            "telemetry": {"latitude": 0.0, "longitude": 0.0, "speed": 0.0, "engine_temp": 0.0, "rpm": 0, "battery_voltage": 0.0},
            "meta": {},
            "route": []
        }
        res = await db.vehicle_locations.insert_one(new_doc)
        real_id = str(res.inserted_id)

    await manager.connect(real_id, hardware_id, websocket)
    await db.vehicle_locations.update_one(
        {"_id": ObjectId(real_id)}, 
        {"$set": {
            "status.online": True, 
            "status.last_update": datetime.now().timestamp(),
            "status.ip_address": client_ip
        }}
    )
    
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "status":
                meta = data.get("meta", {})
                sensors = meta.get("sensors", {})
                gps = sensors.get("gps", {})
                relays = meta.get("relays", {})
                
                lat = float(gps.get("lat", 0.0))
                lon = float(gps.get("lon", 0.0))
                
                # Append to route history if moving or significant change
                if lat != 0.0 and lon != 0.0:
                    await db.vehicle_locations.update_one(
                        {"_id": ObjectId(real_id)},
                        {
                            "$push": {
                                "route": {
                                    "$each": [{
                                        "lat": lat, "lon": lon, 
                                        "timestamp": datetime.now().isoformat(),
                                        "speed": float(gps.get("speed", 0.0))
                                    }],
                                    "$slice": -500 # Keep last 500 points
                                }
                            }
                        }
                    )

                update_doc = {
                    "meta": meta,
                    "status.active": bool(relays.get("0", False)),
                    "status.last_update": datetime.now().timestamp(),
                    "telemetry.latitude": lat,
                    "telemetry.longitude": lon,
                    "telemetry.speed": float(gps.get("speed", 0.0)),
                    "telemetry.engine_temp": float(sensors.get("engine", {}).get("temp", 0.0)),
                    "telemetry.rpm": int(sensors.get("engine", {}).get("rpm", 0)),
                    "telemetry.battery_voltage": float(sensors.get("battery", 0.0))
                }
                await db.vehicle_locations.update_one({"_id": ObjectId(real_id)}, {"$set": update_doc})
    except WebSocketDisconnect:
        manager.disconnect(real_id)
        await db.vehicle_locations.update_one({"_id": ObjectId(real_id)}, {"$set": {"status.online": False, "status.last_update": datetime.now().timestamp()}})
    except Exception as e:
        logging.error(f"WS Error for {real_id}: {e}")
        manager.disconnect(real_id)
        await db.vehicle_locations.update_one({"_id": ObjectId(real_id)}, {"$set": {"status.online": False}})

@app.get("/health")
async def health():
    return {"ok": True}
