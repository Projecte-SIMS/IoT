# Raspberry Pi IoT Management System

**Versión:** Sprint 5  
**Última actualización:** 2026-03-03

Sistema de gestión y control remoto para dispositivos Raspberry Pi mediante un microservicio centralizado en FastAPI, comunicación por WebSockets y persistencia en MongoDB.

---

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
1. **Agentes → FastAPI**: Raspberry Pi envía telemetría vía WebSocket cada 5 segundos
2. **FastAPI ↔ MongoDB**: FastAPI es el ÚNICO que accede a MongoDB
3. **Laravel → FastAPI**: Laravel consulta dispositivos y envía comandos vía HTTP
4. **Frontend → Laravel**: Vue consume la API de Laravel (nunca habla con FastAPI directamente)

---

## 📁 Estructura del Proyecto

```
Raspberry_py/
├── agent/                      # Código que corre en Raspberry Pi
│   ├── agent.py               # Script principal del agente
│   ├── requirements.txt       # Dependencias Python
│   ├── run_agent.sh          # Script de ejecución
│   ├── install_service.sh    # Instalar como servicio systemd
│   ├── Dockerfile
│   └── .env                  # Configuración local
│
├── server/                    # Microservicio FastAPI
│   ├── main.py               # API REST + WebSocket server
│   ├── requirements.txt      # Dependencias Python
│   ├── Dockerfile
│   ├── static/               # Archivos estáticos (vacío)
│   ├── templates/            # Templates Jinja2 (vacío)
│   └── .env                  # Configuración del servidor
│
├── docker-compose.yml         # Orquestación de contenedores
├── requirements.txt           # Dependencias globales
├── README.md                  # Este archivo
├── ESTADO_SUBSISTEMA_IOT.md  # Documentación técnica
└── funcinament_agent.md      # Guía del agente
```

---

## 🚀 Despliegue Rápido (Servidor)

### 1. Requisitos
- Docker y Docker Compose
- Python 3.9+ (para desarrollo local)
- MongoDB Atlas o instancia local

### 2. Configuración del Entorno

```bash
# Copiar configuración de ejemplo
cp .env.example server/.env

# Editar server/.env
MONGO_URI=mongodb+srv://usuario:pass@cluster.mongodb.net/
DB_NAME=raspi_db
API_KEY=TU_CLAVE_SECRETA
```

### 3. Levantar con Docker

```bash
docker-compose up --build
```

El servidor estará disponible en `http://localhost:8001`.

---

## 📡 Configuración del Agente (Raspberry Pi)

El agente es **Plug & Play** y se auto-registra al conectar.

### Instalación Manual

```bash
cd agent

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar .env:
# SERVER_WS=ws://IP_SERVIDOR:8001
# DEVICE_ID=Camion-01 (opcional, se genera automáticamente)

# Ejecutar
./run_agent.sh
```

### Instalar como Servicio

```bash
sudo ./install_service.sh
sudo systemctl enable sims-agent
sudo systemctl start sims-agent
```

### Variables de Entorno del Agente

| Variable | Descripción | Default |
|----------|-------------|---------|
| `SERVER_WS` | URL del servidor WebSocket | `ws://localhost:8001` |
| `DEVICE_ID` | Identificador del dispositivo | Auto-generado por hardware |
| `RELAY0_PIN` | Pin GPIO para el relé | `17` |
| `GPS_PORT` | Puerto serie del GPS | `/dev/ttyS0` |

---

## 🔌 Endpoints del Microservicio

### Lectura (GET) - Sin autenticación

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/devices` | Lista todos los dispositivos |
| `GET /api/devices/{id}/route` | Historial de ruta del dispositivo |
| `GET /health` | Estado del microservicio |

### Comandos (POST) - Requiere API Key

| Endpoint | Descripción |
|----------|-------------|
| `POST /api/command` | Envía comando a un dispositivo |
| `POST /api/devices/{id}/route/clear` | Limpia historial de ruta |

**Header requerido:** `x-api-key: TU_CLAVE_SECRETA`

**Body del comando:**
```json
{
  "device_id": "raspi-xxx",
  "action": "on",   // "on", "off", "reboot"
  "relay": 0        // 0 o 1
}
```

### WebSocket

| Endpoint | Descripción |
|----------|-------------|
| `WS /ws/{hardware_id}` | Conexión para agentes |

---

## 📊 Modelo de Datos MongoDB

Colección: `vehicle_locations`

```json
{
  "_id": "ObjectId",
  "identity": {
    "hardware_id": "raspi-abcd1234",
    "name": "Camion-01",
    "license_plate": "1234ABC"
  },
  "status": {
    "online": true,
    "active": false,
    "last_update": 1709478000
  },
  "telemetry": {
    "latitude": 41.3851,
    "longitude": 2.1734,
    "speed": 45.5,
    "engine_temp": 85.0,
    "rpm": 2500,
    "battery_voltage": 12.6
  },
  "meta": {
    "device_name": "Camion-01",
    "relays": { "0": false },
    "sensors": { ... }
  }
}
```

---

## 📤 Telemetría del Agente

El agente envía datos cada 5 segundos:

```json
{
  "type": "status",
  "meta": {
    "device_name": "raspi-xxx",
    "relays": {
      "0": true
    },
    "sensors": {
      "gps": {
        "lat": 41.3851,
        "lon": 2.1734,
        "speed": 45.5
      },
      "engine": {
        "temp": 85.0,
        "rpm": 2500
      },
      "battery": 12.6
    }
  }
}
```

---

## 🎮 Comandos Soportados

| Acción | Descripción | Efecto |
|--------|-------------|--------|
| `on` | Encender | Activa relé GPIO → Arranca vehículo |
| `off` | Apagar | Desactiva relé GPIO → Para vehículo |
| `reboot` | Reiniciar | Reinicia la Raspberry Pi |

---

## 🔗 Integración con Laravel

Laravel usa `VehicleLocationService.php` para comunicarse:

### Configuración (.env de Laravel)

```env
IOT_MICROSERVICE_URL=http://localhost:8001
IOT_API_KEY=TU_CLAVE_SECRETA
IOT_TIMEOUT=5
```

### Uso en Laravel

```php
$iotService = app(VehicleLocationService::class);

// Obtener todas las ubicaciones
$locations = $iotService->getLocations();

// Obtener un dispositivo
$device = $iotService->getDevice($deviceId);

// Encender/apagar
$result = $iotService->turnOn($deviceId);
$result = $iotService->turnOff($deviceId);

// Enviar comando genérico
$result = $iotService->sendCommand($deviceId, 'reboot');

// Health check
$isOnline = $iotService->healthCheck();

// Vincular dispositivo a vehículo
$result = $iotService->updateDevicePlate($deviceId, '1234ABC');
```

### Endpoints de Laravel para IoT

| Método | Ruta | Descripción | Acceso |
|--------|------|-------------|--------|
| GET | `/api/iot/health` | Estado microservicio | Público |
| GET | `/api/iot/devices` | Lista dispositivos | Autenticado |
| GET | `/api/iot/devices/{id}` | Detalle dispositivo | Autenticado |
| GET | `/api/iot/devices/{id}/ping` | Verificar online | Autenticado |
| POST | `/api/admin/iot/devices/{id}/on` | Encender | Admin |
| POST | `/api/admin/iot/devices/{id}/off` | Apagar | Admin |
| POST | `/api/admin/iot/devices/{id}/command` | Comando genérico | Admin |
| POST | `/api/admin/iot/devices/{id}/link` | Vincular a vehículo | Admin |

---

## ✅ Estado Actual

### Completado
- [x] Servidor FastAPI con WebSocket
- [x] Agente para Raspberry Pi
- [x] Auto-registro de dispositivos
- [x] Telemetría GPS, motor, batería
- [x] Control de relés (on/off)
- [x] Historial de rutas
- [x] Integración con Laravel
- [x] Docker Compose
- [x] Documentación

### Pendiente
- [ ] SSL/TLS para WebSocket en producción
- [ ] Acelerómetro para detección de colisiones
- [ ] Carcasa protectora para hardware

---

## 🔒 Seguridad

- **API Key**: Comandos requieren header `x-api-key`
- **Variables de Entorno**: Credenciales en `.env`, no en código
- **Validación**: Pydantic valida todos los datos de entrada
- **Aislamiento**: Solo FastAPI accede a MongoDB

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Servidor | Python 3.9+, FastAPI, Uvicorn |
| Base de datos | MongoDB Atlas, Motor (async) |
| WebSocket | FastAPI WebSocket |
| Agente | Python 3.9+, websockets, gpiozero |
| GPS | pynmea2, pyserial |
| Contenedores | Docker, Docker Compose |

---

*Este sistema permite la gestión escalable de flotas de vehículos IoT de manera automática y segura.*
