# Documentación del Subsistema de Sensores y Actuadores IoT

**Última actualización:** 2026-03-04

Esta documentación detalla el estado real del desarrollo del subsistema IoT, cumpliendo con los requisitos de diseño, modelado y funcionalidad.

---

## 1. Diagrama de Diseño del Subsistema

El diseño actual sigue una arquitectura de estrella centralizada con comunicación asíncrona:

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
- **Nodo Local (Raspberry Pi):** Agente Python que gestiona GPIO (relés) y lectura de sensores (GPS).
- **Servidor de Control (FastAPI):** Broker de mensajes WebSocket y API REST.
- **Base de Datos (MongoDB):** Almacenamiento del estado persistente y telemetría.

**Estado:** Aprobado y operativo.

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

### Completadas

| Funcionalidad | Descripción | Estado |
|---------------|-------------|--------|
| Posicionamiento GPS | Lectura de coordenadas, velocidad y altitud | Completado |
| Monitorización de Energía | Lectura del voltaje de la batería del vehículo | Completado |
| Estado del Motor | RPM y temperatura (simulada o real según hardware) | Completado |
| Auto-registro | Los dispositivos se registran automáticamente al conectar | Completado |
| Control Remoto | Capacidad para encender y apagar vehículos a distancia | Completado |
| Historial de Rutas | Almacenamiento de los últimos 200 puntos GPS | Completado |
| WebSocket Bidireccional | Envío de telemetría y recepción de comandos en tiempo real | Completado |
| Reconexión Automática | El agente reintenta la conexión si se pierde el enlace | Completado |

### Pendientes

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| SSL/TLS WebSocket | Cifrado de comunicaciones en entorno de producción | Media |
| Acelerómetro | Implementación de detección automática de colisiones | Baja |
| Carcasa Protectora | Diseño de hardware adaptado para automoción | Baja |

---

## 4. Implementación del Actuador ON/OFF

El control de encendido y apagado se realiza mediante un relé de potencia conectado a la Raspberry Pi.

### Hardware
- **Pin GPIO:** 17 (configurable mediante la variable `RELAY0_PIN`).
- **Librería utilizada:** `gpiozero` (incluye un `MockRelay` para pruebas en sistemas sin GPIO).

### Flujo de Ejecución de un Comando

1. El administrador envía una petición `POST /api/admin/iot/devices/{id}/on` desde el backend de Laravel.
2. Laravel invoca el método `turnOn()` de la clase `VehicleLocationService`.
3. El servicio envía una petición `POST /api/command` al microservicio FastAPI con la API Key correspondiente.
4. FastAPI transmite el comando a través del WebSocket activo hacia el agente de la Raspberry Pi.
5. El agente conmuta el pin GPIO y devuelve una confirmación (ACK) al servidor.
6. El estado se actualiza en la base de datos MongoDB (`status.active = true`).
7. Laravel recibe la confirmación final de la operación.

### Ejemplo de código del Agente

```python
# agent/agent.py
if action == "on":
    RELAYS[relay_idx].on()
elif action == "off":
    RELAYS[relay_idx].off()

# Envío de confirmación de estado
ack = {"type": "ack", "payload": {"relay": relay_idx, "state": r.is_active}}
await ws.send(json.dumps(ack))
```

---

## 5. Telemetría del Agente

El agente está configurado para enviar datos de sus sensores cada 5 segundos:

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

## 6. Integración entre Laravel y FastAPI

### Servicio de comunicación: VehicleLocationService.php

El backend de Laravel interactúa con el microservicio mediante los siguientes métodos:

- **getLocations():** Obtiene las ubicaciones de todos los vehículos activos.
- **getAllDevices():** Recupera la lista completa de dispositivos.
- **getDevice(string $deviceId):** Obtiene los detalles de un dispositivo específico.
- **sendCommand(string $deviceId, string $action, int $relay = 0):** Envía un comando (on, off o reboot).
- **turnOn(string $deviceId) / turnOff(string $deviceId):** Métodos abreviados para el control de encendido.
- **healthCheck():** Verifica el estado de salud del microservicio.
- **isDeviceOnline(string $deviceId):** Comprueba si un dispositivo está conectado actualmente.
- **updateDevicePlate(string $deviceId, string $licensePlate):** Vincula un dispositivo a una matrícula específica.

### Endpoints definidos en Laravel (IoTController.php)

Rutas para usuarios autenticados:
- `GET /api/iot/health`: Comprobación de estado.
- `GET /api/iot/devices`: Listado de dispositivos.
- `GET /api/iot/devices/{id}`: Detalle de dispositivo.
- `GET /api/iot/devices/{id}/ping`: Verificación de conexión online.
- `GET /api/iot/logs`: Historial de comandos ejecutados.

Rutas exclusivas para administradores:
- `POST /api/admin/iot/devices/{id}/on`: Encendido remoto.
- `POST /api/admin/iot/devices/{id}/off`: Apagado remoto.
- `POST /api/admin/iot/devices/{id}/command`: Envío de comando genérico.
- `POST /api/admin/iot/devices/{id}/link`: Vinculación a un vehículo.
- `GET /api/admin/iot/devices/unlinked`: Dispositivos pendientes de vinculación.
- `GET /api/admin/iot/vehicles/available`: Lista de vehículos disponibles.

---

## 7. Registro de Comandos (CommandLog)

Todas las acciones de control realizadas por los usuarios se registran en la base de datos PostgreSQL de Laravel para auditoría:

```php
// app/Models/CommandLog.php
CommandLog::create([
    'user_id' => auth()->id(),
    'device_id' => $deviceId,
    'action' => 'on',
    'payload' => [],
    'status' => 'sent', // Estados: 'sent' o 'failed'
]);
```

---

## 8. Configuración del Sistema

### Servidor FastAPI (.env)
```env
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/
DB_NAME=raspi_db
API_KEY=TU_CLAVE_SECRETA
```

### Agente Raspberry Pi (.env)
```env
SERVER_WS=ws://192.168.1.100:8001
DEVICE_ID=Camion-01
RELAY0_PIN=17
GPS_PORT=/dev/ttyS0
```

---

## 9. Medidas de Seguridad

| Medida | Descripción |
|--------|----------------|
| API Key | Uso obligatorio del header `x-api-key` para el envío de comandos |
| Gestión de Secretos | Uso de archivos `.env` para evitar credenciales en el código fuente |
| Validación de Datos | Implementación de esquemas Pydantic para validar entradas |
| Aislamiento de BD | El acceso a MongoDB está restringido exclusivamente a FastAPI |

---

## 10. Próximos Pasos

1. Implementar SSL/TLS para asegurar las comunicaciones por WebSocket.
2. Integrar la lectura de acelerómetros para mejorar la seguridad del vehículo.
3. Finalizar el diseño de la carcasa para protección del hardware en entornos reales.

---

*Documento preparado para la revisión del Sprint 5.*
