# Subsistema IoT SIMS (Multitenant Integration)

**Version:** Sprint 5 – Multitenant Architecture  
**Ultima actualización:** Mayo 2026

Este subsistema gestiona la telemetría y el control remoto de la flota de vehículos. Está diseñado como un microservicio Global que sirve a múltiples organizaciones (tenants) de forma transparente, integrándose en la arquitectura SaaS de SIMS.

---

## Arquitectura y Flujo de Datos

El subsistema IoT opera bajo un modelo Single-Instance / Multi-Data, actuando como un componente agnóstico a los tenants que delega la lógica de aislamiento al backend central:

1.  **Agentes IoT (Raspberry Pi):** Dispositivos embarcados en los vehículos. Cada agente posee un `hardware_id` único e inmutable (ej: `AUTO-001`).
2.  **Servidor IoT (FastAPI):** Microservicio global que mantiene conexiones WebSocket persistentes con los agentes. Centraliza la telemetría en una instancia de MongoDB Atlas. No almacena lógica de pertenencia a tenants, solo asociaciones de `hardware_id`.
3.  **Capa de Aislamiento (Laravel):** El backend multitenant de Laravel mantiene la relación de propiedad entre un `vehicle_id` (dentro del esquema de un tenant) y un `hardware_id` (en el microservicio IoT).

### Integración en la arquitectura SaaS:
- El microservicio FastAPI funciona como una fuente de datos crudos y un puente de comandos.
- El aislamiento se garantiza en el Backend de Laravel: cuando un usuario solicita datos de un vehículo, Laravel identifica el `hardware_id` asociado en el esquema del tenant actual y realiza la petición firmada al microservicio IoT.
- Un tenant solo puede acceder a la telemetría de los dispositivos vinculados explícitamente a su base de datos, garantizando la integridad y privacidad de los datos entre diferentes organizaciones.

---

## Componentes

### 1. Servidor FastAPI (`/server`)
Microservicio asíncrono optimizado para la gestión de tráfico de telemetría de alta frecuencia y baja latencia.
- **URL Producción:** `https://sims-iot-microservice.onrender.com`
- **Tecnología:** Python 3.11, FastAPI, WebSockets, MongoDB Atlas.
- **Rol en SIMS:** Actúa como el orquestador global de comunicaciones IoT, abstrayendo la complejidad de la conexión física de los vehículos del resto de la lógica de negocio.

### 2. Agente IoT (`/agent`)
Software de control embarcado para ejecución en hardware Raspberry Pi.
- **Funciones:** Transmisión de datos GPS, niveles de energía, temperatura y estado del motor. Ejecución de comandos de actuadores (encendido/apagado).
- **Resiliencia:** Mecanismos de reconexión automática con backoff exponencial y supervisión mediante `systemd`.

---

## Integración con el Backend Multitenant

La comunicación entre el ecosistema Laravel y el microservicio IoT se centraliza en la clase `VehicleLocationService.php`.

### Configuración en Laravel (.env):
```env
# URL del microservicio IoT
IOT_MICROSERVICE_URL=https://sims-iot-microservice.onrender.com
# Clave de API para autenticación administrativa
IOT_API_KEY=MACMECMIC
```

### Endpoints de Integración:
- `GET /api/devices`: Consulta global de dispositivos conectados (restringido a IP del backend).
- `POST /api/command`: Envío de directivas de control a un `hardware_id` específico.
- `GET /api/devices/{id}/route`: Recuperación de series temporales de coordenadas para reconstrucción de rutas por tenant.

---

## Gestión de Flota y Despliegue Masivo

Para facilitar el despliegue en múltiples dispositivos y garantizar actualizaciones sencillas, hemos implementado el **SIMS Fleet Manager**.

### 🚀 Despliegue con Fleet Manager

1.  **Configurar Inventario:** Edita el archivo `inventory.json` con la lista de tus Raspberry Pi:
    ```json
    [
      {
        "id": "AUTO-001",
        "ip": "192.168.1.100",
        "user": "pi",
        "tenant_id": "feetly",
        "api_key": "TU_KEY_SEGURA",
        "use_docker": true
      }
    ]
    ```

2.  **Comandos Principales:**
    - **Desplegar/Actualizar Software:** Envía el código más reciente y reinicia el agente.
      ```bash
      python3 fleet_manager.py deploy
      ```
    - **Ver Estado:** Comprueba si los agentes están corriendo.
      ```bash
      python3 fleet_manager.py status
      ```
    - **Actualizar Keys:** Si hay una filtración, actualiza la `IOT_API_KEY` en todos los dispositivos al instante.
      ```bash
      python3 fleet_manager.py update-keys
      ```
    - **Reiniciar Dispositivos:**
      ```bash
      python3 fleet_manager.py reboot
      ```

### 🐳 Despliegue con Docker (Recomendado)

El agente ahora soporta Docker para un entorno aislado y consistente:
- **Archivo:** `agent/docker-compose.yml`
- **Ventaja:** No requiere instalar dependencias manualmente en la Raspberry. Todo lo necesario viene en la imagen.

---


- [**Guía Rápida Raspberry Pi**](./docs/QUICKSTART_RASPBERRY.md) - Configuración inicial de hardware.
- [**Manual del Agente**](./docs/README_AGENT.md) - Especificaciones del script de telemetría.
- [**Guía de Servicio Systemd**](./docs/SERVICE_GUIDE.md) - Persistencia del agente en Linux.
- [**Estado Técnico**](./docs/ESTADO_SUBSISTEMA_IOT.md) - Flujos detallados e integración multitenant.

---
**SIMS IoT Team - Sprint 5**
