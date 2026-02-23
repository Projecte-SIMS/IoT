import asyncio
import json
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import requests
import os

def send_post(url, payload):
    api_key = os.environ.get('API_KEY', 'changeme')
    headers = {'x-api-key': api_key}
    try:
        return requests.post(url, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"Error sending POST to {url}: {e}")
        return None
import os

app = FastAPI()

# In-memory registries (for demo)
agents: Dict[str, Dict[str, Any]] = {}
ws_connections: Dict[str, WebSocket] = {}
pending_futures: Dict[str, asyncio.Future] = {}
cmd_counter = 0

class RegisterModel(BaseModel):
    agent_id: str
    callback_url: str | None = None

class CommandModel(BaseModel):
    cmd: str
    params: Dict[str, Any] | None = None

@app.post('/register')
async def register_agent(payload: RegisterModel):
    agents[payload.agent_id] = {
        'callback_url': payload.callback_url,
        'last_status': None
    }
    return {'status': 'ok', 'agent_id': payload.agent_id}

@app.websocket('/ws/{agent_id}')
async def agent_ws(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    ws_connections[agent_id] = websocket
    # mark registered even if no callback_url
    agents.setdefault(agent_id, {})
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                continue
            # if it's a response to a command, resolve future
            if msg.get('type') == 'response' and msg.get('cmd_id'):
                fut = pending_futures.pop(msg['cmd_id'], None)
                if fut and not fut.done():
                    fut.set_result(msg.get('result'))
            # update last status
            if msg.get('type') == 'status':
                agents.setdefault(agent_id, {})['last_status'] = msg.get('status')
    except WebSocketDisconnect:
        ws_connections.pop(agent_id, None)

@app.post('/agents/{agent_id}/command')
async def send_command(agent_id: str, command: CommandModel):
    global cmd_counter
    info = agents.get(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail='Agent not registered')

    # Prefer WebSocket if available
    ws = ws_connections.get(agent_id)
    cmd_id = f"cmd-{cmd_counter}"
    cmd_counter += 1
    payload = {
        'type': 'command',
        'cmd_id': cmd_id,
        'cmd': command.cmd,
        'params': command.params or {}
    }

    if ws:
        fut = asyncio.get_event_loop().create_future()
        pending_futures[cmd_id] = fut
        await ws.send_text(json.dumps(payload))
        try:
            result = await asyncio.wait_for(fut, timeout=10.0)
            return {'via': 'ws', 'result': result}
        except asyncio.TimeoutError:
            pending_futures.pop(cmd_id, None)
            raise HTTPException(status_code=504, detail='No response from agent via ws')

    # If no ws connection try direct HTTP
    callback_url = info.get('callback_url')
    if callback_url:
        try:
            resp = send_post(callback_url.rstrip('/') + '/execute', payload)
            return {'via': 'http', 'status_code': resp.status_code, 'result': resp.json()}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f'Error contacting agent: {e}')

    raise HTTPException(status_code=503, detail='Agent not connected (no ws and no callback_url)')

@app.get('/agents/{agent_id}/status')
async def get_status(agent_id: str):
    info = agents.get(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail='Agent not registered')
    return {'agent_id': agent_id, 'last_status': info.get('last_status')}
