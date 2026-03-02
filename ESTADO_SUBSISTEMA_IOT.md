# Documentación del Subsistema de Sensores y Actuadores IoT

Esta documentación detalla el estado real del desarrollo del subsistema IoT al finalizar el Sprint 4, cumpliendo con los requisitos de diseño, modelado y funcionalidad.

---

## 1. Diagrama de Diseño del Subsistema
El diseño actual sigue una arquitectura de **estrella centralizada** con comunicación asíncrona:

*   **Nodo Local (Raspberry Pi):** Ejecuta un agente en Python que gestiona el hardware (GPIO para relés) y la lectura de sensores (GPS a través de puerto serie).
*   **Servidor de Control (FastAPI):** Actúa como Broker de mensajes usando WebSockets para tiempo real y expone una API REST para la integración con sistemas externos.
*   **Base de Datos (MongoDB):** Almacena el estado persistente y la telemetría en una colección unificada.

**Flujo de Aprobación:** El diseño está **aprobado y operativo**, permitiendo la comunicación bidireccional (Telemetría de subida / Comandos de bajada).

---

## 2. Modelo de Datos (Estructura MongoDB)
Se utiliza una estructura de documentos anidados en la colección `vehicle_locations` para garantizar la organización y escalabilidad:

```json
{
  "identity": {
    "hardware_id": "ID_UNICO_HW",
    "name": "Alias_Vehiculo",
    "license_plate": "MATRICULA_REAL"
  },
  "status": {
    "online": "boolean",
    "active": "boolean (Estado encendido/apagado)",
    "last_update": "timestamp"
  },
  "telemetry": {
    "latitude": "float",
    "longitude": "float",
    "speed": "float",
    "engine_temp": "float",
    "rpm": "integer",
    "battery_voltage": "float"
  }
}
```

---

## 3. Funcionalidades Aceptadas y Desarrollo Continuo
Tras las pruebas de laboratorio, se han aceptado y estabilizado las siguientes funciones:
*   **Posicionamiento Global (GPS):** Lectura de coordenadas, velocidad y altitud.
*   **Monitorización de Energía:** Control del voltaje de la batería del vehículo.
*   **Estado del Motor:** Lectura de RPM y temperatura (simulada/real vía sensores).
*   **Identificación Automática:** Registro automático de hardware nuevo sin configuración previa.

---

## 4. Implementación del Actuador ON/OFF
El control de encendido/apagado del vehículo se implementa mediante un **Relé de Potencia** controlado por el Agente IoT:
*   **Hardware:** Pin GPIO 17 conectado a un módulo de relé que interrumpe el circuito de encendido del vehículo.
*   **Lógica:** 
    1.  El comando se envía vía API REST al servidor.
    2.  El servidor lo transmite por WebSocket al agente.
    3.  El agente conmuta el pin GPIO y devuelve un `ACK` de confirmación.
    4.  El estado se refleja en el campo `status.active` de la base de datos.

---

## 5. Requerimientos Futuros
Para el siguiente Sprint, se identifica la necesidad de:
1.  **Hardware Final:** Carcasa protectora para la Raspberry Pi y cableado certificado para automoción.
2.  **Sensores Adicionales:** Integración de acelerómetro para detección de colisiones o conducción brusca.
3.  **Seguridad de Red:** Implementación de túneles SSL/TLS para la comunicación WebSocket fuera de la red local.

---

## 6. Integración con Laravel
Siguiendo las directrices del proyecto:
*   **Comunicación:** Laravel consultará los datos de `vehicle_locations` mediante el driver de MongoDB o a través de la API del microservicio.
*   **Frontend:** El Frontend principal del proyecto **no hablará directamente con el subsistema IoT**. Laravel actuará como intermediario, procesando los datos y sirviéndolos al cliente final.

---
*Documento preparado para la revisión de final de Sprint.*
