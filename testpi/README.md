# FastAPI Server + Raspberry Pi Agent

Este repositorio contiene un ejemplo mínimo de:

- Un servidor FastAPI dockerizado que gestiona agentes (Raspberry Pi) y puede enviar comandos a los agentes por dos métodos:
  - Modo directo: el servidor hace POST/GET directo a la URL pública del agente.
  - Modo reverse (recomendado para conexiones celulares/NAT): el agente abre una conexión WebSocket al servidor y el servidor envía comandos a través de esa conexión.

- Un agente Python que corre en la Raspberry Pi que:
  - Expone un endpoint HTTP /execute para recibir comandos directos (si la Pi tiene IP pública o puerto encaminado).
  - Mantiene una conexión WebSocket con el servidor para recibir comandos cuando el servidor no puede contactar al agente directamente.

Estructura de archivos:

- server/: código del servidor FastAPI + Dockerfile
- agent/: código del agente Python para Raspberry Pi

Requisitos:

- Docker (para el servidor)
- Python 3.10+ (para el agente si se ejecuta en la Raspberry Pi sin Docker)

Instrucciones rápidas

1) Construir y ejecutar el servidor con Docker:

  cd server
  docker build -t fastapi-server:latest .
  docker run --rm -p 8000:8000 --env-file .env -e SERVER_HOST=0.0.0.0 -e SERVER_PORT=8000 fastapi-server:latest

  (o usar docker-compose si se prefiere)

2) Ejecutar el agente en la Raspberry Pi (modo recomendado: reverse WebSocket):

  En la Raspberry Pi, instalar dependencias y arrancar el agente apuntando a la URL pública del servidor:

  export SERVER_HTTP=https://mi-servidor-publico.com
  export AGENT_ID=pi-01
  python agent/agent.py

3) Registrar el agente (el agente también intenta auto-registrarse al arrancar). Para registrar manualmente:

  curl -X POST "http://localhost:8000/register" -H "Content-Type: application/json" -d '{"agent_id":"pi-01","callback_url":"http://1.2.3.4:8001"}'

4) Enviar comando al agente (si está conectado por WebSocket, se enviará por WS; si el agente es accesible públicamente, se hará POST directo):

  curl -X POST "http://localhost:8000/agents/pi-01/command" -H "Content-Type: application/json" -d '{"cmd":"relay","params":{"relay":1,"action":"on"}}'


Consideraciones de red (importantes):

- En redes móviles con tarjeta SIM el dispositivo suele quedar detrás de carrier NAT: el servidor no podrá abrir conexiones directas al agente a menos que el operador dé una IP pública o se haga un túnel.
- Opciones:
  - Usar el modo reverse (agente abre WebSocket al servidor). Recomendado.
  - Usar túnel inverso SSH desde la Pi a un host público: ssh -R 9001:localhost:8001 user@publichost
  - Usar ngrok o servicios similares para exponer temporalmente el HTTP del agente.
  - Usar MQTT (no incluido aquí) como alternativa profesional para IoT.

Archivos creados:
- server/app/main.py
- server/Dockerfile
- server/requirements.txt
- server/.env.example
- agent/agent.py
- agent/requirements.txt

Leer abajo para detalles y explicaciones de cada archivo.
