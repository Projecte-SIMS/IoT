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

    async def connect(self, device_id: str, websocket: WebSocket):
        self.active[device_id] = websocket

    def disconnect(self, device_id: str):
        self.active.pop(device_id, None)

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

# API: devices
@app.get("/api/devices")
async def list_devices(token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    docs = []
    cursor = db.vehicle_locations.find({})
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

@app.get("/api/devices/{device_id}")
async def get_device(device_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
        
    device = await db.vehicle_locations.find_one({"_id": obj_id})
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

@app.put("/api/devices/{device_id}")
async def update_device(device_id: str, update: DeviceUpdate, token: str = Header(None, alias="x-api-key")):
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
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
        
    return {"status": "updated"}

@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
        
    # Check if device exists to get its ID for websocket cleanup
    device = await db.vehicle_locations.find_one({"_id": obj_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    # Delete from MongoDB
    await db.vehicle_locations.delete_one({"_id": obj_id})
    
    # Close websocket if active to prevent immediate re-creation via WS loop
    if device_id in manager.active:
        ws = manager.active[device_id]
        try:
            await ws.close(code=1000, reason="Device deleted from system")
        except:
            pass
        manager.disconnect(device_id)
        
    return {"status": "deleted"}

@app.get("/api/ping/{device_id}")
async def ping_device(device_id: str):
    return {"device_id": device_id, "online": device_id in manager.active}

@app.get("/api/devices/{device_id}/route")
async def get_device_route(device_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
    
    device = await db.vehicle_locations.find_one({"_id": obj_id}, {"route": 1})
    if not device:
        return []
    return device.get("route", [])

@app.post("/api/devices/{device_id}/route/clear")
async def clear_device_route(device_id: str, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    try:
        obj_id = ObjectId(device_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid device ID format")
        
    await db.vehicle_locations.update_one({"_id": obj_id}, {"$set": {"route": []}})
    return {"status": "cleared"}

# API: send command
@app.post("/api/command")
async def send_command(cmd: CommandCreate, token: str = Header(None, alias="x-api-key")):
    await verify_token(token)
    
    cmd_doc = cmd.dict()
    cmd_doc["status"] = "pending"
    cmd_doc["created_at"] = datetime.now().isoformat()
    target_id = str(cmd.device_id)
    
    await db.commands.insert_one(cmd_doc)
    if "_id" in cmd_doc:
        cmd_doc["id"] = str(cmd_doc["_id"])
        del cmd_doc["_id"]

    sent = await manager.send_json(target_id, {"type": "command", "payload": cmd_doc})
    if sent:
        await db.commands.update_many({"device_id": cmd.device_id, "status": "pending"}, {"$set": {"status": "sent"}})
        return {"result": "sent"}
    return {"result": "queued"}

# WebSocket for agents
@app.websocket("/ws/{hardware_id}")
async def device_ws(websocket: WebSocket, hardware_id: str, token: str = None):
    # Verify token from query parameter or subprotocol if needed
    # For simplicity, we'll check it from query param ?token=...
    if token != API_KEY:
        await websocket.close(code=1008, reason="Invalid API Key")
        return

    await websocket.accept()

    # Buscar si ya existe un dispositivo con este hardware_id
    device = await db.vehicle_locations.find_one({"identity.hardware_id": hardware_id})

    if device:
        # Si existe, usamos su ID de MongoDB
        real_id = str(device["_id"])
    else:
        # Si no existe, es un dispositivo nuevo. Lo creamos.
        new_doc = {
            "identity": {
                "hardware_id": hardware_id, 
                "name": hardware_id, 
                "license_plate": "AUTO-" + hardware_id[-4:]
            },
            "status": {"online": True, "active": False, "last_update": datetime.now().timestamp()},
            "telemetry": {"latitude": 0.0, "longitude": 0.0, "speed": 0.0, "engine_temp": 0.0, "rpm": 0, "battery_voltage": 0.0},
            "meta": {},
            "route": []
        }
        res = await db.vehicle_locations.insert_one(new_doc)
        real_id = str(res.inserted_id)

    await manager.connect(real_id, websocket)
    await db.vehicle_locations.update_one({"_id": ObjectId(real_id)}, {"$set": {"status.online": True, "status.last_update": datetime.now().timestamp()}})
    
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
