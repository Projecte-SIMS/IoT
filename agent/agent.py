#!/usr/bin/env python3
import os
import json
import asyncio
import logging
import uuid
import random

# Intentar importar librerías de hardware
try:
    from gpiozero import OutputDevice, LED
    HARDWARE_AVAILABLE = True
except Exception:
    HARDWARE_AVAILABLE = False

try:
    import websockets
except Exception:
    websockets = None

def get_unique_id():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    return f"raspi-{line.split(':')[1].strip()}"
    except: pass
    return f"device-{hex(uuid.getnode())[2:]}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# CONFIGURACIÓN
DEVICE_ID = os.getenv("DEVICE_ID") or get_unique_id()
TENANT_ID = os.getenv("TENANT_ID", "default")
SERVER_WS = os.getenv("SERVER_WS")
IOT_API_KEY = os.getenv("DEVICE_TOKEN") or os.getenv("IOT_API_KEY", "MACMECMIC")
RELAY_PIN = int(os.getenv("RELAY0_PIN", 17))
LED_YELLOW_PIN = 20  # Estado: Reservado
LED_GREEN_PIN = 21   # Estado: En Marcha

# Inicialización de Hardware
hw = {}

# GPS Inicial (Evitar 0,0 en el mar si no se especifica)
INITIAL_LAT = float(os.getenv("INITIAL_LAT", 41.3851)) # Barcelona default
INITIAL_LON = float(os.getenv("INITIAL_LON", 2.1734))

class MockHW:
    def on(self): pass
    def off(self): pass
    @property
    def is_active(self): return False

if HARDWARE_AVAILABLE:
    try:
        hw["relay"] = OutputDevice(RELAY_PIN, active_high=True, initial_value=False)
        hw["led_yellow"] = LED(LED_YELLOW_PIN, active_high=True)
        hw["led_green"] = LED(LED_GREEN_PIN, active_high=True)
        logging.info(f"✅ Hardware listo: Relé({RELAY_PIN}), Amarillo({LED_YELLOW_PIN}), Verde({LED_GREEN_PIN})")
    except Exception as e:
        logging.warning(f"⚠️ Error GPIO: {e}. Usando simulación.")
        HARDWARE_AVAILABLE = False

if not HARDWARE_AVAILABLE:
    hw["relay"] = MockHW()
    hw["led_yellow"] = MockHW()
    hw["led_green"] = MockHW()

vehicle_stats = {
    "gps": {"lat": INITIAL_LAT, "lon": INITIAL_LON, "alt": 0.0, "speed": 0.0},
    "engine": {"temp": 20.0, "rpm": 0},
    "battery": 12.6
}

async def read_sensors():
    global vehicle_stats
    while True:
        if hw["relay"].is_active:
            vehicle_stats["engine"]["temp"] = 85.0 + random.random() * 5
            vehicle_stats["engine"]["rpm"] = random.randint(1500, 2500)
        else:
            vehicle_stats["engine"]["temp"] = max(20.0, vehicle_stats["engine"]["temp"] - 0.5)
            vehicle_stats["engine"]["rpm"] = 0
        vehicle_stats["gps"]["lat"] += (random.random() - 0.5) * 0.0001
        vehicle_stats["gps"]["lon"] += (random.random() - 0.5) * 0.0001
        await asyncio.sleep(2)

async def send_status(ws):
    while True:
        try:
            payload = {
                "type": "status", 
                "meta": {
                    "device_name": DEVICE_ID,
                    "relays": {"0": hw["relay"].is_active},
                    "sensors": vehicle_stats,
                    "state": "running" if hw["led_green"].is_active else ("reserved" if hw["led_yellow"].is_active else "idle")
                }
            }
            await ws.send(json.dumps(payload))
            await asyncio.sleep(5)
        except: raise

async def handle_messages(ws):
    async for message in ws:
        try:
            data = json.loads(message)
            if data.get("type") == "command":
                action = data.get("payload", {}).get("action")
                
                if action == "reserve":
                    logging.info("🟡 RESERVADO: LED Amarillo ON")
                    hw["led_yellow"].on()
                    hw["led_green"].off()
                    hw["relay"].off()
                
                elif action == "on":
                    logging.info("🟢 EN MARCHA: LED Verde + Relé ON")
                    hw["led_yellow"].off()
                    hw["led_green"].on()
                    hw["relay"].on()
                
                elif action == "off":
                    logging.info("🟡 PARADA (Sigue reservado): LED Amarillo ON")
                    hw["led_yellow"].on()
                    hw["led_green"].off()
                    hw["relay"].off()
                
                elif action in ["finish", "terminate", "clear"]:
                    logging.info("⚪ FIN DE RESERVA: Todo OFF")
                    hw["led_yellow"].off()
                    hw["led_green"].off()
                    hw["relay"].off()
                
                elif action == "reboot":
                    os.system("sudo reboot")
        except Exception as e:
            logging.warning(f"⚠️ Error: {e}")

async def run():
    # Use token in query param for WebSocket handshake
    # wss://iot-server.com/ws/feetly/AUTO-001?token=...
    uri = f"{SERVER_WS}/ws/{TENANT_ID}/{DEVICE_ID}?token={IOT_API_KEY}"
    while True:
        try:
            logging.info(f"🔄 Conectando a {SERVER_WS}/ws/{TENANT_ID}/{DEVICE_ID}...")
            async with websockets.connect(
                uri, ping_interval=20, ping_timeout=10, open_timeout=15, compression=None
            ) as ws:
                logging.info("✅ CONECTADO")
                tasks = [
                    asyncio.create_task(read_sensors()),
                    asyncio.create_task(send_status(ws)),
                    asyncio.create_task(handle_messages(ws))
                ]
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
                for task in pending: task.cancel()
                for task in done: 
                    if task.exception(): raise task.exception()
        except Exception as e:
            logging.warning(f"❌ Error: {e}. Reintentando en 10s...")
            await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Agente detenido")
