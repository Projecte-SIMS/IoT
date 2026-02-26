#!/usr/bin/env python3
import os
import json
import asyncio
import logging
import uuid

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

def get_unique_id():
    """Genera un ID único basado en el hardware (CPU Serial o MAC)"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    return f"raspi-{line.split(':')[1].strip()}"
    except:
        pass
    
    # Fallback a MAC si no es una Raspberry Pi
    mac = uuid.getnode()
    return f"device-{hex(mac)[2:]}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# CARGA DE CONFIGURACIÓN (Solo desde entorno)
# Si DEVICE_ID no existe, se genera uno automático
DEVICE_ID = os.getenv("DEVICE_ID")
if not DEVICE_ID:
    DEVICE_ID = get_unique_id()
    logging.info(f"Identidad automática generada: {DEVICE_ID}")
else:
    logging.info(f"Identidad manual detectada: {DEVICE_ID}")

# El servidor debe venir del .env, si no, usamos el estándar de Docker/Local
SERVER_WS = os.getenv("SERVER_WS", "ws://localhost:8001")
# El PIN debe ser configurable, por defecto el 17
RELAY0_PIN = int(os.getenv("RELAY0_PIN", "17"))

# Configuración de Relés
RELAYS = {}
if OutputDevice:
    try:
        RELAYS[0] = OutputDevice(RELAY0_PIN, active_high=True, initial_value=False)
    except Exception as e:
        logging.error(f"Error inicializando GPIO {RELAY0_PIN}: {e}")
else:
    class MockRelay:
        def __init__(self): self._v = False
        def on(self): self._v = True; logging.info("Mock Relay ON")
        def off(self): self._v = False; logging.info("Mock Relay OFF")
        def is_active(self): return self._v
    RELAYS[0] = MockRelay()
    logging.info("Usando MockRelay (No se detectó hardware GPIO)")

async def send_status(ws):
    """Bucle de envío de telemetría"""
    try:
        while True:
            payload = {
                "type": "status", 
                "meta": {
                    "device_name": DEVICE_ID,
                    "relays": {str(k): RELAYS[k].is_active() for k in RELAYS}
                }
            }
            await ws.send(json.dumps(payload))
            await asyncio.sleep(10)
    except Exception as e:
        logging.debug(f"Status sender error: {e}")

async def handle_messages(ws):
    """Bucle de escucha de comandos"""
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
                    
                    # Respuesta de confirmación
                    ack = {"type": "ack", "payload": {"relay": relay_idx, "state": r.is_active()}}
                    await ws.send(json.dumps(ack))
        except Exception as e:
            logging.warning(f"Error procesando mensaje: {e}")

async def run():
    if not websockets:
        logging.error("Librería 'websockets' no instalada.")
        return

    uri = f"{SERVER_WS}/ws/{DEVICE_ID}"
    while True:
        try:
            logging.info(f"Conectando a {uri}...")
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                # Enviar saludo inicial
                await ws.send(json.dumps({"type": "status", "meta": {"event": "online"}}))
                
                # Ejecutar emisor y receptor en paralelo
                await asyncio.gather(send_status(ws), handle_messages(ws))
        except Exception as e:
            logging.warning(f"Conexión perdida: {e}. Reintentando en 5s...")
            await asyncio.sleep(5)

if __name__ == '__main__':
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Agente detenido por el usuario.")
