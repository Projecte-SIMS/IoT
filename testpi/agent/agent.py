import asyncio
import os
import json
from typing import Dict, Any
import requests
import os

def send_post(url, payload):
    api_key = os.environ.get('API_KEY', 'changeme')
    headers = {'x-api-key': api_key}
    try:
        return requests.post(url, json=payload, headers=headers, timeout=3)
    except Exception as e:
        print(f"Error sending POST to {url}: {e}")
        return None
import os
from fastapi import FastAPI, Request
import uvicorn
import websockets

SERVER_HTTP = os.environ.get('SERVER_HTTP', 'http://localhost:8000')
AGENT_ID = os.environ.get('AGENT_ID', 'pi-01')
DIRECT_PORT = int(os.environ.get('DIRECT_PORT', '8001'))

app = FastAPI()
state: Dict[str, Any] = {"relays": {}}

@app.post('/execute')
async def execute(request: Request):
    body = await request.json()
    # body expected to have type, cmd, cmd_id, params
    cmd = body.get('cmd')
    params = body.get('params') or {}
    result = handle_command(cmd, params)
    return {'status': 'ok', 'result': result}

def handle_command(cmd: str, params: Dict[str, Any]):
    # Simula control de relés y lectura de estados
    if cmd == 'relay':
        r = params.get('relay')
        action = params.get('action')
        if r is None or action not in ('on', 'off'):
            return {'error': 'invalid params'}
        state['relays'][str(r)] = (action == 'on')
        return {'relay': r, 'state': state['relays'][str(r)]}
    # Comandos adicionales aquí
    return {'error': 'unknown cmd'}

async def ws_client():
    # Conecta al servidor para modo reverse
    ws_url = SERVER_HTTP.replace('http://', 'ws://').replace('https://', 'wss://') + f'/ws/{AGENT_ID}'
    try:
        async with websockets.connect(ws_url) as ws:
            # notify server of registration via HTTP
            try:
                send_post(SERVER_HTTP + '/register', {'agent_id': AGENT_ID, 'callback_url': f'http://{get_local_ip()}:{DIRECT_PORT}'})
            except Exception:
                pass
            while True:
                text = await ws.recv()
                try:
                    msg = json.loads(text)
                except Exception:
                    continue
                if msg.get('type') == 'command':
                    res = handle_command(msg.get('cmd'), msg.get('params') or {})
                    # enviar respuesta
                    response = {'type': 'response', 'cmd_id': msg.get('cmd_id'), 'result': res}
                    await ws.send(json.dumps(response))
    except Exception:
        await asyncio.sleep(5)
        # reconnect loop
        await ws_client()

def get_local_ip():
    # intento simple de obtener IP local para callback_url (puede fallar en NAT)
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

if __name__ == '__main__':
    # iniciar cliente websocket en background y API HTTP para modo directo
    loop = asyncio.get_event_loop()
    loop.create_task(ws_client())
    uvicorn.run(app, host='0.0.0.0', port=DIRECT_PORT)
