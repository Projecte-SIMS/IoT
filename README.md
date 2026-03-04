# Raspberry Pi IoT Management System

**Versión:** Sprint 5  
**Última actualización:** 2026-03-04

Sistema de gestión y control remoto para dispositivos Raspberry Pi mediante un microservicio centralizado en FastAPI, comunicación por WebSockets y persistencia en MongoDB.

---

## Arquitectura del Sistema

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
│                 │                    │   (Puerto 8000)  │     (Usuarios, Reservas)
└─────────────────┘                    └─────────────────┘
```

**Flujo de datos:**
1. **Agentes -> FastAPI**: Raspberry Pi envía telemetría vía WebSocket cada 5 segundos.
2. **FastAPI <-> MongoDB**: FastAPI es el único componente que accede a la base de datos MongoDB.
3. **Laravel -> FastAPI**: Laravel consulta el estado de los dispositivos y envía comandos mediante peticiones HTTP.
4. **Frontend -> Laravel**: La interfaz en Vue consume la API de Laravel y nunca se comunica directamente con FastAPI.

---

## Estructura del Proyecto

```
Raspberry_py/
├── agent/                      # Código que se ejecuta en la Raspberry Pi
│   ├── agent.py               # Script principal del agente
│   ├── requirements.txt       # Dependencias de Python para el agente
│   ├── run_agent.sh          # Script de ejecución del agente
│   ├── install_service.sh    # Instalador para servicio systemd
│   ├── Dockerfile
│   └── .env                  # Configuración local del agente
│
├── server/                    # Microservicio FastAPI
│   ├── main.py               # Servidor API REST y WebSocket
│   ├── requirements.txt       # Dependencias de Python para el servidor
│   ├── Dockerfile
│   ├── static/               # Archivos estáticos (JavaScript del Dashboard)
│   ├── templates/            # Plantillas Jinja2 (HTML del Dashboard)
│   └── .env                  # Configuración del servidor
│
├── docker-compose.yml         # Orquestación de contenedores
├── requirements.txt           # Dependencias globales
├── README.md                  # Este archivo
├── ESTADO_SUBSISTEMA_IOT.md  # Documentación técnica detallada
└── funcinament_agent.md      # Guía de funcionamiento del agente
```

---

## Despliegue Rápido (Servidor)

### 1. Requisitos
- Docker y Docker Compose
- Python 3.9 o superior (para desarrollo local)
- Cuenta en MongoDB Atlas o una instancia local de MongoDB

### 2. Configuración del Entorno

```bash
# Copiar configuración de ejemplo
cp .env.example server/.env

# Editar server/.env con los datos correspondientes
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/
DB_NAME=raspi_db
API_KEY=TU_CLAVE_SECRETA
```

### 3. Ejecución con Docker

```bash
docker-compose up --build
```

El servidor estará disponible en la dirección `http://localhost:8001`.

---

## Configuración del Agente (Raspberry Pi)

El agente es Plug & Play y se registra automáticamente al establecer conexión.

### Instalación Manual

```bash
cd agent

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env:
# SERVER_WS=ws://IP_DEL_SERVIDOR:8001
# DEVICE_ID=Camion-01 (opcional, se genera automáticamente si se deja vacío)

# Ejecutar el agente
./run_agent.sh
```

### Instalación como Servicio del Sistema

```bash
sudo ./install_service.sh
sudo systemctl enable sims-agent
sudo systemctl start sims-agent
```

### Variables de Entorno del Agente

| Variable | Descripción | Valor por defecto |
|----------|-------------|---------|
| `SERVER_WS` | URL del servidor WebSocket | `ws://localhost:8001` |
| `DEVICE_ID` | Identificador único del dispositivo | Generado por hardware |
| `RELAY0_PIN` | Pin GPIO utilizado para el relé | `17` |
| `GPS_PORT` | Puerto serie para el módulo GPS | `/dev/ttyS0` |

---

## Endpoints del Microservicio

### Lectura (GET) - Sin autenticación

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/devices` | Devuelve la lista de todos los dispositivos registrados |
| `GET /api/devices/{id}/route` | Devuelve el historial de ruta de un dispositivo |
| `GET /health` | Comprueba el estado de salud del microservicio |

### Comandos (POST) - Requiere API Key

| Endpoint | Descripción |
|----------|-------------|
| `POST /api/command` | Envía un comando de control a un dispositivo |
| `POST /api/devices/{id}/route/clear` | Elimina el historial de ruta almacenado |

**Cabecera requerida:** `x-api-key: TU_CLAVE_SECRETA`

**Cuerpo del comando (JSON):**
```json
{
  "device_id": "raspi-xxx",
  "action": "on",   // Opciones: "on", "off", "reboot"
  "relay": 0        // Índice del relé (por defecto 0)
}
```

### WebSocket

| Endpoint | Descripción |
|----------|-------------|
| `WS /ws/{hardware_id}` | Punto de conexión para los agentes |

---

## Modelo de Datos en MongoDB

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

## Telemetría del Agente

El agente envía actualizaciones de estado cada 5 segundos con el siguiente formato:

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

## Comandos Soportados

| Acción | Descripción | Efecto en el hardware |
|--------|-------------|-----------------------|
| `on` | Encender | Activa el relé GPIO, permitiendo el arranque del vehículo |
| `off` | Apagar | Desactiva el relé GPIO, deteniendo el vehículo |
| `reboot` | Reiniciar | Ejecuta un reinicio completo de la Raspberry Pi |

---

## Integración con Laravel

El sistema Laravel utiliza la clase `VehicleLocationService.php` para la comunicación:

### Configuración (Archivo .env de Laravel)

```env
IOT_MICROSERVICE_URL=http://localhost:8001
IOT_API_KEY=TU_CLAVE_SECRETA
IOT_TIMEOUT=5
```

### Ejemplos de uso en Laravel

```php
$iotService = app(VehicleLocationService::class);

// Obtener todas las ubicaciones actuales
$locations = $iotService->getLocations();

// Obtener detalles de un dispositivo específico
$device = $iotService->getDevice($deviceId);

// Controlar el encendido o apagado
$resultOn = $iotService->turnOn($deviceId);
$resultOff = $iotService->turnOff($deviceId);

// Enviar comandos genéricos como reiniciar
$resultReboot = $iotService->sendCommand($deviceId, 'reboot');

// Verificar la disponibilidad del microservicio
$isOnline = $iotService->healthCheck();

// Vincular un identificador de dispositivo a una matrícula
$resultLink = $iotService->updateDevicePlate($deviceId, '1234ABC');
```

---

## Estado Actual del Proyecto

### Funcionalidades Completadas
- Servidor FastAPI con soporte para WebSockets.
- Agente Python optimizado para Raspberry Pi.
- Sistema de auto-registro de nuevos dispositivos.
- Transmisión de telemetría (GPS, estado del motor, voltaje de batería).
- Control remoto de actuadores (relés para encendido/apagado).
- Almacenamiento y consulta del historial de rutas.
- Integración completa con el backend de Laravel.
- Contenerización mediante Docker Compose.
- Documentación técnica actualizada.

### Tareas Pendientes
- Implementación de cifrado SSL/TLS para las conexiones WebSocket en producción.
- Integración de acelerómetro para la detección automática de colisiones.
- Diseño y fabricación de carcasa protectora para el hardware.

---

## Seguridad

- **Clave de API**: Todos los comandos de control requieren la cabecera `x-api-key`.
- **Variables de Entorno**: Las credenciales se gestionan en archivos `.env` y nunca se incluyen en el código fuente.
- **Validación de Datos**: Se utiliza Pydantic para validar estrictamente todos los datos de entrada en el servidor.
- **Aislamiento de Red**: Solo el servidor FastAPI tiene permisos de acceso a la base de datos MongoDB.

---

## Stack Tecnológico

| Componente | Tecnología utilizada |
|------------|------------|
| Servidor | Python 3.9+, FastAPI, Uvicorn |
| Base de datos | MongoDB Atlas, Motor (driver asíncrono) |
| Comunicación en tiempo real | FastAPI WebSockets |
| Agente | Python 3.9+, websockets, gpiozero |
| Gestión de GPS | pynmea2, pyserial |
| Despliegue | Docker, Docker Compose |

---

*Este sistema permite la gestión escalable de flotas de vehículos mediante tecnología IoT de manera automática y segura.*
