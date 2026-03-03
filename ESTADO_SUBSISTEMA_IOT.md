# Documentación del Subsistema de Sensores y Actuadores IoT

**Última actualización:** 2026-03-03

Esta documentación detalla el estado real del desarrollo del subsistema IoT, cumpliendo con los requisitos de diseño, modelado y funcionalidad.

---

## 1. Diagrama de Diseño del Subsistema

El diseño actual sigue una arquitectura de **estrella centralizada** con comunicación asíncrona:

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│  Raspberry Pi   │ ◄───────────────► │  FastAPI Server │◄──── MongoDB Atlas
│    (Agentes)    │    Telemetría      │   (Puerto 8001) │
└─────────────────┘    + Comandos      └────────┬────────┘
                                                │
                                                │ HTTP REST + API Key
                                                │
                                       ┌────────▼────────┐
                                       │  Laravel Backend │
                                       │   (Puerto 8000)  │
                                       └─────────────────┘
```

**Componentes:**
- **Nodo Local (Raspberry Pi):** Agente Python que gestiona GPIO (relés) y lectura de sensores (GPS)
- **Servidor de Control (FastAPI):** Broker de mensajes WebSocket + API REST
- **Base de Datos (MongoDB):** Estado persistente y telemetría

**Estado:** ✅ Aprobado y operativo

---

## 2. Modelo de Datos (MongoDB)

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

## 3. Funcionalidades Implementadas

### ✅ Completadas

| Funcionalidad | Descripción | Estado |
|---------------|-------------|--------|
| Posicionamiento GPS | Lectura de coordenadas, velocidad, altitud | ✅ |
| Monitorización de Energía | Voltaje de batería del vehículo | ✅ |
| Estado del Motor | RPM y temperatura (simulada/real) | ✅ |
| Auto-registro | Dispositivos se registran automáticamente | ✅ |
| Control Remoto | Encender/apagar vehículos | ✅ |
| Historial de Rutas | Almacena últimos 200 puntos GPS | ✅ |
| WebSocket Bidireccional | Telemetría + comandos en tiempo real | ✅ |
| Reconexión Automática | Agente reconecta si pierde conexión | ✅ |

### ⚠️ Pendientes

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| SSL/TLS WebSocket | Cifrado en producción | Media |
| Acelerómetro | Detección de colisiones | Baja |
| Carcasa Protectora | Hardware para automoción | Baja |

---

## 4. Implementación del Actuador ON/OFF

El control de encendido/apagado se implementa mediante un **Relé de Potencia**:

### Hardware
- **Pin GPIO:** 17 (configurable via `RELAY0_PIN`)
- **Librería:** gpiozero (con MockRelay para pruebas)

### Flujo de Comando

```
1. Admin envía POST /api/admin/iot/devices/{id}/on desde Laravel
2. Laravel llama a VehicleLocationService.turnOn()
3. VehicleLocationService envía POST /api/command al microservicio
4. FastAPI transmite comando por WebSocket al agente
5. Agente conmuta GPIO y envía ACK
6. Estado se actualiza en MongoDB (status.active = true)
7. Laravel recibe confirmación
```

### Código del Agente

```python
# agent/agent.py
if action == "on":
    RELAYS[relay_idx].on()
elif action == "off":
    RELAYS[relay_idx].off()

# Enviar confirmación
ack = {"type": "ack", "payload": {"relay": relay_idx, "state": r.is_active}}
await ws.send(json.dumps(ack))
```

---

## 5. Telemetría del Agente

El agente envía datos cada **5 segundos**:

```python
payload = {
    "type": "status",
    "meta": {
        "device_name": DEVICE_ID,
        "relays": {str(k): RELAYS[k].is_active for k in RELAYS},
        "sensors": {
            "gps": {"lat": lat, "lon": lon, "speed": speed},
            "engine": {"temp": temp, "rpm": rpm},
            "battery": voltage
        }
    }
}
await ws.send(json.dumps(payload))
```

---

## 6. Integración Laravel ↔ FastAPI

### Servicio: VehicleLocationService.php

```php
class VehicleLocationService
{
    // Obtener ubicaciones de todos los vehículos
    public function getLocations(): array

    // Obtener todos los dispositivos
    public function getAllDevices(): array

    // Obtener un dispositivo específico
    public function getDevice(string $deviceId): ?array

    // Enviar comando (on/off/reboot)
    public function sendCommand(string $deviceId, string $action, int $relay = 0): array

    // Atajos para on/off
    public function turnOn(string $deviceId): array
    public function turnOff(string $deviceId): array

    // Health check del microservicio
    public function healthCheck(): bool

    // Verificar si dispositivo está online
    public function isDeviceOnline(string $deviceId): bool

    // Vincular dispositivo a vehículo
    public function updateDevicePlate(string $deviceId, string $licensePlate): array
}
```

### Controlador: IoTController.php

```php
// Endpoints autenticados
GET  /api/iot/health              // Health check
GET  /api/iot/devices             // Lista dispositivos
GET  /api/iot/devices/{id}        // Detalle dispositivo
GET  /api/iot/devices/{id}/ping   // Verificar online
GET  /api/iot/logs                // Logs de comandos

// Endpoints admin
POST /api/admin/iot/devices/{id}/on       // Encender
POST /api/admin/iot/devices/{id}/off      // Apagar
POST /api/admin/iot/devices/{id}/command  // Comando genérico
POST /api/admin/iot/devices/{id}/link     // Vincular a vehículo
GET  /api/admin/iot/devices/unlinked      // Dispositivos sin vincular
GET  /api/admin/iot/vehicles/available    // Vehículos disponibles
```

---

## 7. Logs de Comandos (CommandLog)

Todos los comandos se registran en PostgreSQL:

```php
// app/Models/CommandLog.php
CommandLog::create([
    'user_id' => auth()->id(),
    'device_id' => $deviceId,
    'action' => 'on',
    'payload' => [],
    'status' => 'sent', // 'sent' o 'failed'
]);
```

---

## 8. Configuración

### Servidor FastAPI (.env)

```env
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=raspi_db
API_KEY=TU_CLAVE_SECRETA
```

### Agente Raspberry (.env)

```env
SERVER_WS=ws://192.168.1.100:8001
DEVICE_ID=Camion-01
RELAY0_PIN=17
GPS_PORT=/dev/ttyS0
```

### Laravel Backend (.env)

```env
IOT_MICROSERVICE_URL=http://localhost:8001
IOT_API_KEY=TU_CLAVE_SECRETA
IOT_TIMEOUT=5
```

---

## 9. Seguridad

| Medida | Implementación |
|--------|----------------|
| API Key | Header `x-api-key` requerido para comandos |
| Variables de Entorno | Credenciales en `.env`, no en código |
| Validación | Pydantic valida datos de entrada |
| Aislamiento | Solo FastAPI accede a MongoDB |
| Rate Limiting | Implementado en Laravel |

---

## 10. Próximos Pasos

| Prioridad | Tarea | Esfuerzo |
|-----------|-------|----------|
| 🟠 Media | SSL/TLS para WebSocket en producción | 4h |
| 🟡 Baja | Acelerómetro para colisiones | 8h |
| 🟡 Baja | Carcasa protectora certificada | Hardware |

---

*Documento preparado para la revisión de Sprint 5.*
