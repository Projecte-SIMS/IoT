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

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = os.getenv("DB_NAME", "raspi_db")
API_KEY = os.getenv("API_KEY", "changeme")  # Debe configurarse en entorno de producción

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

app = FastAPI()
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
    await db.commands.insert_one(cmd_doc)
    sent = await manager.send_json(cmd.device_id, {"type": "command", "payload": cmd_doc})
    if sent:
        await db.commands.update_many({"device_id": cmd.device_id, "status": "pending"}, {"$set": {"status": "sent"}})
        logging.info(f"Command sent: {cmd_doc}")
        return {"result": "sent"}
    logging.info(f"Command queued: {cmd_doc}")
    return {"result": "queued"}

# WebSocket for agents
@app.websocket("/ws/{device_id}")
async def device_ws(websocket: WebSocket, device_id: str):
    await manager.connect(device_id, websocket)
    # mark device online
    try:
        await db.devices.update_one({"_id": ObjectId(device_id)}, {"$set": {"online": True}}, upsert=False)
    except Exception:
        pass
    try:
        while True:
            data = await websocket.receive_json()
            # expect device to send status updates or command acks
            typ = data.get("type")
            if typ == "status":
                try:
                    await db.devices.update_one({"_id": ObjectId(device_id)}, {"$set": {"meta": data.get("meta", {})}}, upsert=False)
                except Exception:
                    pass
            elif typ == "ack":
                # update command status
                try:
                    await db.commands.update_one({"device_id": device_id, "status": "sent"}, {"$set": {"status": "ack"}})
                except Exception:
                    pass
    except WebSocketDisconnect:
        manager.disconnect(device_id)
        try:
            await db.devices.update_one({"_id": ObjectId(device_id)}, {"$set": {"online": False}}, upsert=False)
        except Exception:
            pass
    except Exception:
        manager.disconnect(device_id)
        try:
            await db.devices.update_one({"_id": ObjectId(device_id)}, {"$set": {"online": False}}, upsert=False)
        except Exception:
            pass

# Simple health
@app.get("/health")
async def health():
    try:
        await client.admin.command("ping")
        return {"ok": True}
    except Exception:
        return {"ok": False}
