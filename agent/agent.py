#!/usr/bin/env python3
import os
import json
import asyncio
import logging
import uuid
import random # Para simular sensores si no hay hardware

# Intentar importar librerías de hardware
try:
    import gpiozero
    OutputDevice = gpiozero.OutputDevice
except Exception:
    OutputDevice = None

try:
    import websockets
except Exception:
    websockets = None

# Librería para GPS (puedes instalarla con pip install pynmea2)
try:
    import pynmea2
    import serial
except Exception:
    pynmea2 = None

def get_unique_id():
    """Genera un ID único basado en el hardware"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    return f"raspi-{line.split(':')[1].strip()}"
    except:
        pass
    mac = uuid.getnode()
    return f"device-{hex(mac)[2:]}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# CONFIGURACIÓN
DEVICE_ID = os.getenv("DEVICE_ID") or get_unique_id()
SERVER_WS = os.getenv("SERVER_WS", "ws://localhost:8001")
RELAY0_PIN = int(os.getenv("RELAY0_PIN", "17"))
GPS_PORT = os.getenv("GPS_PORT", "/dev/ttyS0") # Puerto serie típico en RPi

# Inicialización de Relés
RELAYS = {}
if OutputDevice:
    try:
        RELAYS[0] = OutputDevice(RELAY0_PIN, active_high=True, initial_value=False)
    except Exception as e:
        logging.error(f"Error GPIO: {e}")
else:
    class MockRelay:
        def __init__(self): self._v = False
        def on(self): self._v = True
        def off(self): self._v = False
        def is_active(self): return self._v
    RELAYS[0] = MockRelay()

# Estado global de sensores
vehicle_stats = {
    "gps": {"lat": 0.0, "lon": 0.0, "alt": 0.0, "speed": 0.0},
    "engine": {"temp": 0.0, "rpm": 0},
    "battery": 12.6
}

async def read_gps():
    """Simulación o lectura real de GPS"""
    global vehicle_stats
    if pynmea2:
        try:
            # Configuración real de puerto serie para GPS
            ser = serial.Serial(GPS_PORT, baudrate=9600, timeout=0.5)
            while True:
                data = ser.readline().decode('ascii', errors='replace')
                if data.startswith('$GPRMC') or data.startswith('$GPGGA'):
                    msg = pynmea2.parse(data)
                    vehicle_stats["gps"]["lat"] = getattr(msg, 'latitude', 0.0)
                    vehicle_stats["gps"]["lon"] = getattr(msg, 'longitude', 0.0)
                    vehicle_stats["gps"]["speed"] = getattr(msg, 'spd_over_grnd', 0.0)
                await asyncio.sleep(1)
        except Exception as e:
            logging.debug(f"GPS Hardware no disponible: {e}")
    
    # Si no hay hardware, simulamos un movimiento leve para pruebas
    while True:
        vehicle_stats["gps"]["lat"] += (random.random() - 0.5) * 0.0001
        vehicle_stats["gps"]["lon"] += (random.random() - 0.5) * 0.0001
        vehicle_stats["engine"]["temp"] = 85.0 + random.random() * 5
        vehicle_stats["engine"]["rpm"] = random.randint(800, 3000)
        await asyncio.sleep(2)

async def send_status(ws):
    """Envío de telemetría completa (Relés + Sensores)"""
    try:
        while True:
            payload = {
                "type": "status", 
                "meta": {
                    "device_name": DEVICE_ID,
                    "relays": {str(k): RELAYS[k].is_active() for k in RELAYS},
                    "sensors": vehicle_stats # Enviamos los datos del vehículo
                }
            }
            await ws.send(json.dumps(payload))
            await asyncio.sleep(5) # Más frecuente para GPS
    except Exception as e:
        logging.debug(f"Status sender error: {e}")

async def handle_messages(ws):
    async for message in ws:
        try:
            data = json.loads(message)
            if data.get("type") == "command":
                payload = data.get("payload", {})
                action = payload.get("action")
                relay_idx = int(payload.get("relay", 0))
                r = RELAYS.get(relay_idx)
                if r:
                    if action == "on": r.on()
                    elif action == "off": r.off()
                    ack = {"type": "ack", "payload": {"relay": relay_idx, "state": r.is_active()}}
                    await ws.send(json.dumps(ack))
        except Exception as e:
            logging.warning(f"Error mensaje: {e}")

async def run():
    if not websockets: return
    uri = f"{SERVER_WS}/ws/{DEVICE_ID}"
    while True:
        try:
            async with websockets.connect(uri) as ws:
                # Ejecutar lectura de GPS, envío de estado y escucha de comandos
                await asyncio.gather(
                    read_gps(),
                    send_status(ws),
                    handle_messages(ws)
                )
        except Exception as e:
            await asyncio.sleep(5)

if __name__ == '__main__':
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
