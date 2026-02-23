#!/usr/bin/env python3
"""
Simple Raspberry agent that connects to FastAPI WebSocket at /ws/{device_id}.
Environment variables:
 - DEVICE_ID: unique id for this device (required)
 - SERVER_WS: base websocket URL, e.g. ws://your.server:8000 (default: ws://localhost:8000)
 - RELAY0_PIN: GPIO pin number for relay 0 (default: 17)

This agent sends periodic status updates and listens for commands of the shape:
{ "type": "command", "payload": { "action": "on"|"off", "relay": 0 } }

When a command is executed the agent sends an ack:
{ "type": "ack", "payload": { "relay": 0, "state": true } }
"""
import os
import json
import asyncio
import logging

try:
    import gpiozero
    OutputDevice = gpiozero.OutputDevice
except Exception:
    OutputDevice = None

try:
    import websockets
except Exception:
    websockets = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DEVICE_ID = os.getenv("DEVICE_ID")
if not DEVICE_ID:
    raise SystemExit("DEVICE_ID environment variable is required")

SERVER_WS = os.getenv("SERVER_WS", "ws://localhost:8000")
RELAY0_PIN = int(os.getenv("RELAY0_PIN", "17"))

# setup relay(s)
RELAYS = {}
if OutputDevice:
    RELAYS[0] = OutputDevice(RELAY0_PIN, active_high=True, initial_value=False)
else:
    class MockRelay:
        def __init__(self):
            self._v = False
        def on(self):
            self._v = True
        def off(self):
            self._v = False
        def is_active(self):
            return self._v
    RELAYS[0] = MockRelay()

async def send_status(ws):
    try:
        while True:
            payload = {"type": "status", "meta": {"relays": {str(k): RELAYS[k].is_active() for k in RELAYS}}}
            await ws.send(json.dumps(payload))
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logging.debug("status sender stopped: %s", e)

async def handle_messages(ws):
    async for message in ws:
        try:
            data = json.loads(message)
        except Exception:
            logging.warning("invalid message: %s", message)
            continue
        typ = data.get("type")
        if typ == "command":
            payload = data.get("payload", {})
            action = payload.get("action")
            relay = int(payload.get("relay", 0))
            logging.info("cmd for relay %s: %s", relay, action)
            r = RELAYS.get(relay)
            if not r:
                logging.warning("unknown relay %s", relay)
                continue
            if action == "on":
                r.on()
            elif action == "off":
                r.off()
            # ack
            ack = {"type": "ack", "payload": {"relay": relay, "state": r.is_active()}}
            await ws.send(json.dumps(ack))
        else:
            logging.debug("unhandled type: %s", typ)

async def run():
    if not websockets:
        raise SystemExit("websockets package required; install with 'pip install websockets'")
    uri = f"{SERVER_WS}/ws/{DEVICE_ID}"
    while True:
        try:
            logging.info("connecting to %s", uri)
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                # send initial status
                await ws.send(json.dumps({"type": "status", "meta": {"startup": True}}))
                sender = asyncio.create_task(send_status(ws))
                handler = asyncio.create_task(handle_messages(ws))
                done, pending = await asyncio.wait([sender, handler], return_when=asyncio.FIRST_EXCEPTION)
                for p in pending:
                    p.cancel()
        except Exception as e:
            logging.warning("connection failed: %s", e)
            await asyncio.sleep(5)

if __name__ == '__main__':
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
