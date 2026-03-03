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

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = os.getenv("DB_NAME", "raspi_db")
API_KEY = os.getenv("API_KEY", "MACMECMIC")

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

# In-memory storage for current session breadcrumbs
# In a real app, this should be in MongoDB
route_history: Dict[str, List[Dict[str, Any]]] = {}

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
class CommandCreate(BaseModel):
    device_id: str
    action: str
    relay: int = 0

# API: devices
@app.get("/api/devices")
async def list_devices():
    docs = []
    cursor = db.vehicle_locations.find({})
    async for d in cursor:
        id_str = str(d["_id"])
        docs.append({
            "id": id_str,
            "name": d["identity"]["name"],
            "hardware_id": d["identity"]["hardware_id"],
            "license_plate": d["identity"]["license_plate"],
            "online": id_str in manager.active,
            "meta": d.get("meta", {}),
            "telemetry": d.get("telemetry", {}),
            "status": d.get("status", {})
        })
    return docs

@app.get("/api/devices/{device_id}/route")
async def get_device_route(device_id: str):
    return route_history.get(device_id, [])

@app.post("/api/devices/{device_id}/route/clear")
async def clear_device_route(device_id: str):
    route_history[device_id] = []
    return {"status": "cleared"}

# API: send command
@app.post("/api/command")
async def send_command(cmd: CommandCreate, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    cmd_doc = cmd.dict()
    cmd_doc["status"] = "pending"
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
async def device_ws(websocket: WebSocket, hardware_id: str):
    device = await db.vehicle_locations.find_one({"identity.hardware_id": hardware_id})

    if not device:
        new_doc = {
            "identity": {"hardware_id": hardware_id, "name": hardware_id, "license_plate": "AUTO-" + hardware_id[-4:]},
            "status": {"online": True, "active": False, "last_update": 0},
            "telemetry": {"latitude": 0.0, "longitude": 0.0, "speed": 0.0, "engine_temp": 0.0, "rpm": 0, "battery_voltage": 0.0},
            "meta": {}
        }
        res = await db.vehicle_locations.insert_one(new_doc)
        real_id = str(res.inserted_id)
    else:
        real_id = str(device["_id"])

    await manager.connect(real_id, websocket)
    await db.vehicle_locations.update_one({"_id": ObjectId(real_id)}, {"$set": {"status.online": True}})
    
    if real_id not in route_history:
        route_history[real_id] = []

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "status":
                meta = data.get("meta", {})
                sensors = meta.get("sensors", {})
                gps = sensors.get("gps", {})
                relays = meta.get("relays", {})
                
                lat, lon = gps.get("lat", 0.0), gps.get("lon", 0.0)
                
                # Append to route history if moving or significant change
                if lat != 0.0 and lon != 0.0:
                    route_history[real_id].append({
                        "lat": lat, "lon": lon, "timestamp": datetime.now().isoformat(),
                        "speed": gps.get("speed", 0.0)
                    })
                    # Keep only last 200 points to avoid memory issues in this simple version
                    if len(route_history[real_id]) > 200:
                        route_history[real_id].pop(0)

                update_doc = {
                    "meta": meta,
                    "status.active": relays.get("0", False),
                    "status.last_update": asyncio.get_event_loop().time(),
                    "telemetry.latitude": lat,
                    "telemetry.longitude": lon,
                    "telemetry.speed": gps.get("speed", 0.0),
                    "telemetry.engine_temp": sensors.get("engine", {}).get("temp", 0.0),
                    "telemetry.rpm": sensors.get("engine", {}).get("rpm", 0),
                    "telemetry.battery_voltage": sensors.get("battery", 0.0)
                }
                await db.vehicle_locations.update_one({"_id": ObjectId(real_id)}, {"$set": update_doc})
    except WebSocketDisconnect:
        manager.disconnect(real_id)
        await db.vehicle_locations.update_one({"_id": ObjectId(real_id)}, {"$set": {"status.online": False}})
    except Exception:
        manager.disconnect(real_id)

@app.get("/health")
async def health():
    return {"ok": True}
