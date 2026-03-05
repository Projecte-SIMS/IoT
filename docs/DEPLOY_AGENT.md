# 🤖 Guía de Deploy del Agente IoT en Raspberry Pi

## ✅ Resumen de Mejoras

El agente ahora tiene:
- 🌐 Reconexión automática cuando hay internet
- ⏰ Backoff exponencial (5s → 60s entre reintentos)
- 🔍 Verificación de internet antes de conectar
- 📊 Logs mejorados
- 🎯 Configuración fácil para producción/local

---

## 🚀 Deploy en Raspberry Pi

### Paso 1: Copiar archivos a la Raspberry Pi

Desde tu Mac/PC:

```bash
# Reemplaza "pi@192.168.1.100" con tu usuario@ip de la Raspberry
scp -r agent/ pi@192.168.1.100:~/sims-agent/
```

---

### Paso 2: Conectar a la Raspberry Pi

```bash
ssh pi@192.168.1.100
cd ~/sims-agent
```

---

### Paso 3: Configurar para Producción

```bash
# Usar configuración de producción (Render)
cp .env.production .env

# Verificar que SERVER_WS apunta a Render
cat .env
```

Debe mostrar:
```
SERVER_WS=wss://sims-iot-microservice.onrender.com
```

---

### Paso 4: Ejecutar el Agente

```bash
# Dar permisos al script
chmod +x run_agent_auto.sh

# Ejecutar en modo producción
./run_agent_auto.sh prod
```

Deberías ver:
```
🌐 Modo PRODUCCIÓN: Conectando a Render (wss://)
✅ Configuración cargada desde: .env.production
📊 CONFIGURACIÓN DEL AGENTE:
   • Device ID: [Auto-generado]
   • Servidor:  wss://sims-iot-microservice.onrender.com
   • Relay Pin: 17
🚀 Iniciando agente IoT...
🔄 Conectando a wss://...
✅ ¡CONEXIÓN ESTABLECIDA CON EL SERVIDOR!
```

---

### Paso 5: Instalar como Servicio (Opcional)

Para que se ejecute automáticamente al iniciar la Raspberry Pi:

```bash
# Editar SERVER_WS en install_service.sh primero
nano install_service.sh

# Cambiar a:
# SERVER_WS=wss://sims-iot-microservice.onrender.com

# Instalar servicio
sudo ./install_service.sh

# Verificar estado
sudo systemctl status sims-agent

# Ver logs en tiempo real
sudo journalctl -u sims-agent -f
```

---

## 🧪 Test de Conexión

### Verificar que el microservicio está activo:

```bash
curl https://sims-iot-microservice.onrender.com/api/devices
```

Debe devolver JSON con lista de dispositivos.

### Verificar WebSocket:

```bash
# Instalar wscat si no lo tienes
npm install -g wscat

# Test WebSocket
wscat -c wss://sims-iot-microservice.onrender.com/ws/test-device
```

---

## 🔄 Comportamiento con Pérdida de Red

### Escenario 1: Sin Internet al Iniciar
```
⚠️ Sin conexión a internet. Esperando 10s...
⚠️ Sin conexión a internet. Esperando 10s...
🔄 Conectando a wss://...
✅ ¡CONEXIÓN ESTABLECIDA!
```

### Escenario 2: Se Pierde Internet Durante Ejecución
```
✅ ¡CONEXIÓN ESTABLECIDA!
❌ Conexión perdida: Connection lost
🔄 Reintentando en 5s...
⚠️ Sin conexión a internet. Esperando 10s...
🔄 Conectando a wss://...
✅ ¡CONEXIÓN ESTABLECIDA!
```

### Escenario 3: Servidor Render Dormido (Plan Gratuito)
```
🔄 Conectando a wss://...
❌ Error WebSocket: Connection refused
🔄 Reintentando en 5s...
🔄 Reintentando en 7s...
🔄 Reintentando en 11s...
✅ ¡CONEXIÓN ESTABLECIDA!  # Después de que Render despertó
```

---

## 📊 Monitoreo

### Ver dispositivo en el Dashboard Web:

1. Abre: https://frontend-nine-orcin-waqisje40z.vercel.app
2. Login: admin@sims.com / password
3. Ve a Admin → Dispositivos IoT
4. Deberías ver tu dispositivo con estado "Online" (verde)

### Ver telemetría:

- GPS actualizado cada 5s
- Temperatura del motor
- RPM
- Voltaje de batería

---

## 🛑 Detener el Agente

```bash
# Si está corriendo en terminal
Ctrl + C

# Si está como servicio
sudo systemctl stop sims-agent

# Desinstalar servicio
sudo systemctl disable sims-agent
sudo rm /etc/systemd/system/sims-agent.service
sudo systemctl daemon-reload
```

---

## 📝 Logs y Debugging

### Ver logs en tiempo real:

```bash
# Si corre en terminal
# Los logs se muestran directamente

# Si corre como servicio
sudo journalctl -u sims-agent -f

# Ver últimas 100 líneas
sudo journalctl -u sims-agent -n 100
```

---

## 🎯 URLs de Producción

| Servicio | URL |
|----------|-----|
| Frontend | https://frontend-nine-orcin-waqisje40z.vercel.app |
| Backend API | https://sims-backend-api.onrender.com/api |
| **IoT Microservice** | **https://sims-iot-microservice.onrender.com** |
| IoT WebSocket | **wss://sims-iot-microservice.onrender.com/ws/{device_id}** |
| IoT API Docs | https://sims-iot-microservice.onrender.com/docs |

---

## ✅ Resultado Esperado

Cuando todo funcione:

✅ Agente conecta automáticamente al iniciar
✅ Si se pierde internet, espera y reconecta
✅ Dashboard muestra dispositivo "Online"
✅ Telemetría se actualiza en tiempo real
✅ Comandos remotos funcionan (on/off)
✅ Logs claros y detallados

---

**¡Tu agente IoT está listo para reconexión automática y producción!** 🚀🤖
