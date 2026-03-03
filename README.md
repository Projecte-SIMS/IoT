# Raspberry Pi IoT Management System

Sistema de gestión y control remoto para dispositivos Raspberry Pi mediante un microservicio centralizado en FastAPI, comunicación por WebSockets y persistencia en MongoDB.

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│  Raspberry Pi   │ ◄───────────────► │  FastAPI Server │◄──── MongoDB Atlas
│    (Agentes)    │    Telemetría      │   (Puerto 8001) │      (Solo FastAPI
└─────────────────┘    + Comandos      └────────┬────────┘       accede a Mongo)
     (Internet)                                 │
                                                │ HTTP REST
                                                │ + API Key
                                                │
┌─────────────────┐      API REST      ┌────────▼────────┐
│  Vue Frontend   │ ◄───────────────► │  Laravel Backend │──── PostgreSQL
│                 │                    │   (Puerto 8000)  │     (Users, Reservas)
└─────────────────┘                    └─────────────────┘
```

**Flujo de datos:**
1. **Agentes → FastAPI**: Raspberry Pi envía telemetría vía WebSocket
2. **FastAPI ↔ MongoDB**: FastAPI es el ÚNICO que accede a MongoDB
3. **Laravel → FastAPI**: Laravel consulta dispositivos y envía comandos vía HTTP
4. **Frontend → Laravel**: Vue consume la API de Laravel (nunca habla con FastAPI directamente)

## 🚀 Despliegue Rápido (Servidor)

### 1. Requisitos
*   Docker y Docker Compose.
*   (Opcional) Raspberry Pi con Python 3.9+ para el agente físico.

### 2. Configuración del Entorno
Copia el archivo de ejemplo y configura tu `API_KEY` y `MONGO_URI`:
```bash
cp .env.example server/.env
```
*   **API_KEY:** Clave de seguridad para autorizar comandos desde Laravel.
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

## 🔒 Seguridad

*   **Control de Acceso:** Los comandos críticos requieren el header `x-api-key`. Sin esta clave, nadie puede apagar/encender tus dispositivos.
*   **Variables de Entorno:** Todas las credenciales están protegidas en archivos `.env` y no están grabadas en el código fuente.
*   **Validación:** Uso de Pydantic para asegurar que los datos recibidos tienen el formato correcto.
*   **Comunicación Laravel:** Laravel se autentica con la misma API_KEY para enviar comandos.

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

### Lectura (GET)
| Endpoint | Descripción | Autenticación |
|----------|-------------|---------------|
| `GET /api/devices` | Lista todos los dispositivos y su estado | Ninguna |
| `GET /api/devices/{id}` | Detalle de un dispositivo | Ninguna |
| `GET /api/ping/{id}` | Verifica si dispositivo está online | Ninguna |
| `GET /health` | Estado del microservicio | Ninguna |

### Comandos (POST) - Requiere API Key
| Endpoint | Descripción | Header |
|----------|-------------|--------|
| `POST /api/command` | Envía acción a un dispositivo | `x-api-key` |

**Body del comando:**
```json
{
  "device_id": "device-123",
  "action": "on",  // "on", "off", "reboot"
  "relay": 0       // 0 o 1
}
```

### WebSocket (Agentes)
*   `GET /ws/{device_id}`: Punto de conexión WebSocket para los agentes.

---

## 🔗 Integración con Laravel

Laravel accede a este microservicio mediante HTTP REST:

**Configuración en Laravel (.env):**
```env
IOT_MICROSERVICE_URL=http://localhost:8001
IOT_API_KEY=MACMECMIC
IOT_TIMEOUT=10
```

**Endpoints en Laravel:**
- `GET /api/iot/devices` - Lista dispositivos
- `GET /api/iot/devices/{id}` - Detalle dispositivo
- `POST /api/admin/iot/devices/{id}/on` - Encender (solo Admin)
- `POST /api/admin/iot/devices/{id}/off` - Apagar (solo Admin)

---

*Este sistema permite la gestión escalable de flotas de vehículos IoT de manera automática y segura.*
