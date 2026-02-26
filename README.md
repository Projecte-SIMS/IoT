# Raspberry Pi IoT Management System

Sistema de gestión y control remoto para dispositivos Raspberry Pi mediante un microservicio centralizado en FastAPI, comunicación por WebSockets y persistencia en MongoDB.

## 🚀 Despliegue Rápido (Servidor)

### 1. Requisitos
*   Docker y Docker Compose.
*   (Opcional) Raspberry Pi con Python 3.9+ para el agente físico.

### 2. Configuración del Entorno
Copia el archivo de ejemplo y configura tu `API_KEY` y `MONGO_URI`:
```bash
cp .env.example server/.env
```
*   **API_KEY:** Clave de seguridad para autorizar comandos desde la web.
*   **MONGO_URI:** Dirección de tu base de datos MongoDB (Local o Atlas).

### 3. Levantar con Docker
```bash
docker-compose up --build
```
El servidor estará disponible en `http://localhost:8001`. (Puerto 8001 para evitar conflictos con Laravel).

---

## 📡 Configuración del Agente (Raspberry Pi)

El agente es **Plug & Play** y se auto-registra al conectar.

### Instalación Manual (Recomendado):
1.  Navega a la carpeta del agente: `cd agent`
2.  Crea un entorno virtual: `python3 -m venv venv && source venv/bin/activate`
3.  Instala dependencias: `pip install -r requirements.txt`
4.  Configura el archivo `agent/.env` con la IP del servidor:
    ```bash
    SERVER_URL=192.168.1.XX:8001
    DEVICE_ID=Camion-01 (Opcional, se genera uno por hardware si se deja vacío)
    ```
5.  Ejecuta: `./run_agent.sh`

> **Nota sobre GPIO:** Si recibes errores de "PEP 668", usa siempre el entorno virtual (`venv`) como se indica arriba.

---

## 🏗️ Arquitectura y Flujo de Datos

El sistema utiliza una arquitectura de **estrella** basada en **eventos en tiempo real**:

1.  **Registro Automático:** Al conectar, el agente envía su ID único (Hardware Serial/MAC). Si el servidor no lo conoce, lo crea en MongoDB instantáneamente.
2.  **Telemetría (Agente → Servidor):** Cada 10 segundos, el agente reporta el estado de sus relés. El servidor actualiza la DB y la web lo muestra.
3.  **Comandos (Web → Servidor → Agente):** 
    *   La Web envía un `POST /api/command` con la `API_KEY`.
    *   El servidor busca el socket activo de la Raspberry.
    *   El comando viaja por el WebSocket y la Raspberry actúa sobre el GPIO.
    *   La Raspberry responde con un `ack` para confirmar la acción.

---

## 🔒 Seguridad
*   **Control de Acceso:** Los comandos críticos requieren el header `x-api-key`. Sin esta clave, nadie puede apagar/encender tus dispositivos.
*   **Variables de Entorno:** Todas las credenciales están protegidas en archivos `.env` y no están grabadas en el código fuente.
*   **Validación:** Uso de Pydantic para asegurar que los datos recibidos tienen el formato correcto.

---

## 🛠️ Stack Tecnológico
| Componente | Tecnologías |
| :--- | :--- |
| **Backend** | Python, FastAPI, WebSockets, Motor (MongoDB) |
| **Frontend** | HTML5, Vanilla CSS, JS (Template system) |
| **Hardware** | Python, GPIO Zero (con MockRelay para pruebas en PC) |
| **Contenedores** | Docker, Docker Compose |

---

## 📋 Endpoints API Principales
*   `GET /api/devices`: Lista todos los dispositivos y su estado online.
*   `POST /api/command`: Envía una acción (on/off) a un dispositivo (Requiere `x-api-key`).
*   `GET /ws/{device_id}`: Punto de conexión WebSocket para los agentes.

---
*Este sistema permite la gestión escalable de flotas de vehículos IoT de manera automática y segura.*
