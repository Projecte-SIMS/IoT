# 🤖 Subsistema IoT - Raspberry Pi

**Versión:** Sprint 4 - Production Ready  
**Última actualización:** 2026-03-05

Sistema de gestión y control remoto de dispositivos Raspberry Pi mediante WebSockets, con microservicio FastAPI y persistencia en MongoDB.

---

## 📋 Índice

- [Descripción General](#-descripción-general)
- [Arquitectura](#-arquitectura)
- [Componentes](#-componentes)
- [Quick Start](#-quick-start)
- [Documentación](#-documentación)
- [Estado del Proyecto](#-estado-del-proyecto)

---

## 🎯 Descripción General

Este subsistema permite:
- 📡 **Telemetría en tiempo real** (GPS, temperatura, RPM, batería)
- 🔌 **Control remoto** de vehículos (encendido/apagado)
- 🔄 **Reconexión automática** del agente
- 📊 **Almacenamiento** de historial de rutas
- 🌐 **Despliegue en la nube** (Render + MongoDB Atlas)

---

## 🏗️ Arquitectura

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│  Raspberry Pi   │ ◄───────────────► │  FastAPI Server │
│    (Agente)     │    wss://          │   (Render)      │◄──── MongoDB Atlas
└─────────────────┘                    └────────┬────────┘
                                                 │
                                                 │ HTTP REST
                                                 │
 ┌─────────────────┐                    ┌────────▼────────┐
 │  Vue Frontend   │ ◄───────────────► │  Laravel Backend │
 │    (Vercel)     │                    │   (Render)      │──── PostgreSQL
 └─────────────────┘                    └─────────────────┘
```

**URLs de Producción:**
- 🌐 **Microservicio IoT:** https://sims-iot-microservice.onrender.com
- 🌐 **Backend API:** https://sims-backend-api.onrender.com
- 🌐 **Frontend:** https://frontend-nine-orcin-waqisje40z.vercel.app

---

## 📦 Componentes

### 1. Servidor FastAPI (`/server`)

Microservicio que gestiona las conexiones WebSocket y expone API REST.

**Archivos principales:**
- `main.py` - Servidor con API REST y WebSocket
- `Dockerfile` - Imagen para Render
- `requirements.txt` - Dependencias Python

**Despliegue:** Render (https://sims-iot-microservice.onrender.com)

### 2. Agente IoT (`/agent`)

Script Python que corre en la Raspberry Pi para enviar telemetría y recibir comandos.

**Archivos principales:**
- `agent.py` - Script principal con reconexión automática
- `run_agent_auto.sh` - Ejecución manual con auto-setup
- `install_service.sh` - Instalación como servicio systemd
- `.env.production` - Config para producción (Render)
- `.env.local` - Config para desarrollo local

**Características:**
- ✅ Reconexión automática (backoff exponencial 5s → 60s)
- ✅ Verificación de internet antes de conectar
- ✅ Ping/pong para mantener conexión viva
- ✅ Auto-registro en el servidor

### 3. Documentación (`/docs`)

Toda la documentación del subsistema IoT organizada por temas.

---

## 🚀 Quick Start

### Para Desarrolladores (Local)

**Requisitos:**
- Docker y Docker Compose
- Python 3.9 o superior (para desarrollo local)
- Cuenta en MongoDB Atlas o instancia local de MongoDB

**Ejecución:**
```bash
# Levantar servidor local
docker-compose up --build

# El servidor estará en: http://localhost:8001
```

**Configuración del servidor (.env):**
```bash
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/
DB_NAME=raspi_db
API_KEY=TU_CLAVE_SECRETA
```

### Para Raspberry Pi (Producción)

Ver **[📖 Guía Rápida para Raspberry Pi](./docs/QUICKSTART_RASPBERRY.md)**

**Resumen:**
```bash
# 1. Copiar archivos
scp -r agent/ pi@raspberry-ip:~/sims-agent/

# 2. Ejecutar
ssh pi@raspberry-ip
cd ~/sims-agent
./run_agent_auto.sh prod

# 3. (Opcional) Instalar como servicio
sudo ./install_service.sh
```

---

## 📡 API REST del Microservicio

### Endpoints Públicos (Sin autenticación)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/devices` | Lista todos los dispositivos registrados |
| GET | `/api/devices/{device_id}` | Detalle de un dispositivo específico |
| GET | `/api/ping/{device_id}` | Verifica si un dispositivo está online |
| GET | `/api/devices/{id}/route` | Historial de ruta de un dispositivo |
| GET | `/health` | Estado de salud del microservicio |

### Endpoints Protegidos (Requiere API Key)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/command` | Envía un comando de control a un dispositivo |
| POST | `/api/devices/{id}/route/clear` | Elimina el historial de ruta |

**Cabecera requerida:** `x-api-key: TU_CLAVE_SECRETA`

**Ejemplo de comando:**
```json
{
  "device_id": "raspi-xxx",
  "action": "on",   // Opciones: "on", "off", "reboot"
  "relay": 0
}
```

### WebSocket

| Endpoint | Descripción |
|----------|-------------|
| `WS /ws/{hardware_id}` | Conexión para agentes IoT |

**Ver más detalles técnicos en:** [docs/ESTADO_SUBSISTEMA_IOT.md](./docs/ESTADO_SUBSISTEMA_IOT.md)

---

## 🔗 Integración con Laravel

El backend Laravel se comunica con el microservicio mediante `VehicleLocationService.php`.

**Configuración (.env de Laravel):**
```env
IOT_MICROSERVICE_URL=https://sims-iot-microservice.onrender.com
IOT_API_KEY=TU_CLAVE_SECRETA
IOT_TIMEOUT=5
```

**Ejemplos de uso:**
```php
$iotService = app(VehicleLocationService::class);

// Obtener ubicaciones
$locations = $iotService->getLocations();

// Controlar dispositivo
$iotService->turnOn($deviceId);
$iotService->turnOff($deviceId);
$iotService->sendCommand($deviceId, 'reboot');

// Verificar disponibilidad
$isOnline = $iotService->healthCheck();
```

**Ver documentación completa:** [docs/ESTADO_SUBSISTEMA_IOT.md](./docs/ESTADO_SUBSISTEMA_IOT.md)

---

## 📚 Documentación

### 🎯 Para Empezar

| Documento | Descripción | Cuándo usarlo |
|-----------|-------------|---------------|
| **[Guía Rápida](./docs/QUICKSTART_RASPBERRY.md)** | Instalación paso a paso en Raspberry Pi | ⭐ Primer deploy |
| **[Guía de Deploy](./docs/DEPLOY_AGENT.md)** | Deploy detallado con todas las opciones | Deploy avanzado |

### 🔧 Configuración y Uso

| Documento | Descripción |
|-----------|-------------|
| **[Guía del Agente](./docs/README_AGENT.md)** | Documentación completa del agente |
| **[Guía del Servicio](./docs/SERVICE_GUIDE.md)** | Instalación y gestión del servicio systemd |

### 📖 Referencia Técnica

| Documento | Descripción |
|-----------|-------------|
| **[Estado del Subsistema](./docs/ESTADO_SUBSISTEMA_IOT.md)** | Arquitectura técnica detallada |
| **[Funcionamiento del Agente](./docs/funcinament_agent.md)** | Detalles internos del agente |

---

## 📊 Estado del Proyecto

### ✅ Funcionalidades Completadas

**Sprint 4 (Producción):**
- ✅ Servidor FastAPI desplegado en Render
- ✅ Agente con reconexión automática
- ✅ Verificación de internet antes de conectar
- ✅ Backoff exponencial para reconexiones (5s → 60s)
- ✅ Servicio systemd mejorado con auto-setup
- ✅ Configuración dual (producción/local)
- ✅ Integración completa con Laravel Backend

**Funcionalidades Core:**
- ✅ WebSocket con ping/pong para mantener conexión
- ✅ Transmisión de telemetría (GPS, motor, batería)
- ✅ Control remoto de actuadores (on/off)
- ✅ Historial de rutas en MongoDB
- ✅ Auto-registro de dispositivos

### 🔜 Próximas Funcionalidades

- 🔲 SSL/TLS para WebSocket en producción
- 🔲 Detección de colisiones (acelerómetro)
- 🔲 Carcasa protectora para hardware

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Servidor | Python 3.11, FastAPI, Uvicorn |
| Base de datos | MongoDB Atlas, Motor (async) |
| Comunicación | WebSockets (wss://) |
| Agente | Python 3.11, websockets, gpiozero |
| Despliegue | Render, Docker |
| Monitoreo | Systemd (journalctl) |

---

## 📞 Soporte

Para más información, consulta la [documentación completa](./docs/) o abre un issue en GitHub.

---

**Sistema SIMS - Subsistema IoT** 🚀  
Proyecto educativo - CFGS DAW
