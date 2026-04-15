# Documentación del Subsistema de Sensores y Actuadores IoT

**Ultima actualización:** 2026-05-15

Esta documentación detalla el estado actual del desarrollo del subsistema IoT, su arquitectura multitenant y el flujo de datos entre el hardware y el ecosistema SIMS SaaS.

---

## 1. Arquitectura del Sistema y Flujo de Datos

El diseño sigue una arquitectura de estrella centralizada donde el microservicio IoT (FastAPI) actúa como un puente global de comunicaciones entre el hardware físico y la infraestructura multitenant de Laravel.

```
┌───────────────────┐     WebSocket      ┌───────────────────┐
│   Raspberry Pi    │ <────────────────> │  FastAPI Microserv│ <─── MongoDB Atlas
│     (Agentes)     │    Telemetría      │   (Microservicio) │
└───────────────────┘    + Comandos      └────────┬──────────┘
                                                  │
                                                  │ HTTP REST + API Key
                                                  │ (Validación de Hardware ID)
                                                  │
                                         ┌────────▼──────────┐
                                         │  Laravel Backend  │
                                         │   (Multitenant)   │
                                         └────────┬──────────┘
                                                  │
                                         ┌────────┴──────────┐
                                         │ Tenant DB Schemas │
                                         │ (Postgres/Oracle) │
                                         └───────────────────┘
```

### Flujo de Datos IoT-Multitenant:
1.  **Origen de Datos:** La Raspberry Pi envía telemetría cada 5 segundos al Servidor FastAPI mediante WebSockets persistentes, identificándose con su `hardware_id`.
2.  **Persistencia Global:** FastAPI almacena estos datos en un MongoDB centralizado. Este microservicio no conoce a qué tenant pertenece el vehículo; solo gestiona identidades de hardware.
3.  **Aislamiento de Negocio:** El Backend de Laravel mantiene en el esquema de cada tenant (ej: `tenant_empresa_a`) la relación entre un vehículo y un `hardware_id`.
4.  **Consumo de Datos:** Cuando un usuario de un tenant solicita la ubicación de su flota, Laravel consulta sus propios esquemas para obtener los IDs de hardware permitidos y realiza peticiones firmadas al microservicio IoT para recuperar exclusivamente esos datos.

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
| Historial de Rutas | Almacenamiento de series temporales de coordenadas | Completado |
| WebSocket Bidireccional | Envío de telemetría y recepción de comandos en tiempo real | Completado |
| Reconexión Automática | Gestión de resiliencia ante pérdida de enlace | Completado |

### Pendientes

| Funcionalidad | Descripción | Prioridad |
|---------------|-------------|-----------|
| SSL/TLS WebSocket | Cifrado de comunicaciones en producción | Media |
| Acelerómetro | Detección automática de colisiones | Baja |
| Carcasa Protectora | Diseño industrial adaptado para automoción | Baja |

---

## 4. Implementación del Actuador ON/OFF

El control de encendido y apagado se realiza mediante un relé de potencia conectado a la Raspberry Pi.

### Hardware
- **Pin GPIO:** 17 (configurable mediante `RELAY0_PIN`).
- **Librería:** `gpiozero`.

### Flujo de Ejecución Multitenant de un Comando

1. Un administrador autenticado en un tenant envía una petición `POST /api/admin/iot/devices/{id}/on`.
2. Laravel verifica que el `{id}` pertenezca al esquema del tenant actual.
3. Laravel invoca el método `turnOn()` de `VehicleLocationService`.
4. El servicio envía una petición `POST /api/command` al microservicio FastAPI autenticada con la API Key global.
5. FastAPI transmite el comando mediante el WebSocket asociado al `hardware_id`.
6. El agente de la Raspberry Pi conmuta el pin GPIO y devuelve un ACK.
7. El estado se actualiza en MongoDB y se propaga al frontend del tenant.

---

## 5. Integración entre Laravel y FastAPI

### Servicio de comunicación: VehicleLocationService.php

El backend de Laravel actúa como el orquestador que dota de contexto de negocio a los datos IoT:

- **getLocations():** Recupera ubicaciones de los dispositivos permitidos para el tenant actual.
- **getAllDevices():** Listado global limitado a administradores centrales.
- **sendCommand(string $deviceId, string $action, int $relay = 0):** Puente de comandos hacia FastAPI.
- **healthCheck():** Monitorización de disponibilidad del microservicio.
- **updateDevicePlate(string $deviceId, string $licensePlate):** Sincronización de metadatos entre el esquema del tenant y el microservicio IoT.

### Endpoints en Laravel (IoTController.php)

Rutas para usuarios de inquilino (Tenant-Aware):
- `GET /api/iot/health`: Estado del subsistema.
- `GET /api/iot/devices`: Dispositivos del inquilino.
- `GET /api/iot/devices/{id}`: Telemetría en tiempo real.
- `GET /api/iot/logs`: Auditoría de comandos del inquilino.

Rutas de Administración Central (SuperAdmin):
- `POST /api/admin/iot/devices/{id}/link`: Vinculación de un dispositivo nuevo a un tenant específico.
- `GET /api/admin/iot/devices/unlinked`: Dispositivos en stock sin asignar a ningún cliente SaaS.

---

## 6. Registro de Comandos y Auditoría

Todas las acciones de control se registran en la base de datos PostgreSQL del inquilino correspondiente para garantizar la trazabilidad por organización:

```php
// Registro en el esquema del inquilino
CommandLog::create([
    'user_id' => auth()->id(),
    'device_id' => $deviceId,
    'action' => 'on',
    'status' => 'sent',
]);
```

---

## 7. Seguridad y Aislamiento

| Medida | Descripción |
|--------|----------------|
| API Key Global | Autenticación entre el backend de Laravel y el microservicio FastAPI |
| Aislamiento SaaS | Laravel actúa como filtro obligatorio; el microservicio IoT no expone datos directamente a los usuarios finales |
| Esquemas de Tenant | Los metadatos de los dispositivos están físicamente aislados por inquilino en PostgreSQL |
| Validación Pydantic | Validación de integridad en la ingesta de telemetría en FastAPI |

---

*Documentación técnica preparada para el cierre del Sprint 5.*
