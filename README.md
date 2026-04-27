# SIMS IoT – Ecosistema de Telemetría

Este ecosistema gestiona la comunicación en tiempo real entre el hardware físico (Raspberry Pi) y el backend multitenant.

## 📡 Estructura del Proyecto
- **`/server` (FastAPI):** Microservicio que gestiona WebSockets y persiste datos en MongoDB. Actúa como puente global de telemetría.
- **`/agent` (Python):** Software embarcado para vehículos. Incluye lógica de reconexión automática y control de periféricos.

## 🚀 Despliegue del Agente (Raspberry Pi)
Utilice el `fleet_manager.py` para automatizar el despliegue en múltiples dispositivos:

```bash
# 1. Configurar inventario en inventory.json
# 2. Desplegar en un dispositivo específico
python3 fleet_manager.py deploy --id RASPI-001
```

### Configuración del Agente (`.env`)
```env
DEVICE_ID=raspi-001
TENANT_ID=nombre-empresa
SERVER_WS=wss://sims-iot.onrender.com
RELAY0_PIN=17
```

## 🛠️ Desarrollo Local
Para probar el flujo completo sin hardware real:
1. Inicie el servidor: `cd server && uvicorn main:app --port 8001`
2. Inicie el agente simulado: `cd agent && ./run_agent_auto.sh local`

## 📄 Documentación Técnica
- [**Manual IoT Centralizado**](https://github.com/Projecte-SIMS/.github/blob/main/profile/docs/iot.md)
- [**Estado del Subsistema IoT**](./docs/ESTADO_SUBSISTEMA_IOT.md)
- [**Guía de Instalación del Agente**](./docs/README_AGENT.md)

---
*Para más detalles, consulta el [README principal](https://github.com/Projecte-SIMS/.github/blob/main/profile/readme.md).*
