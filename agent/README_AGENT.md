# 🤖 Agente IoT - Guía de Configuración y Uso

## 📋 Descripción

El agente IoT es un script Python que se ejecuta en la Raspberry Pi para:
- 📡 Enviar telemetría (GPS, temperatura, RPM, batería)
- 🔌 Recibir comandos remotos (encender/apagar relés)
- 🔄 Reconectarse automáticamente cuando se pierde la conexión
- 🌐 Verificar conexión a internet antes de conectar

---

## 🚀 Configuración Rápida

### Paso 1: Configura el entorno

El agente tiene 3 configuraciones disponibles:

#### **Para PRODUCCIÓN (Raspberry Pi → Render):**
```bash
# Usa .env.production (ya configurado para Render)
cp .env.production .env
```

#### **Para DESARROLLO LOCAL:**
```bash
# Usa .env.local (ya configurado para localhost)
cp .env.local .env
```

#### **Personalizado:**
```bash
# Edita .env manualmente
nano .env
```

---

### Paso 2: Ejecutar el Agente

#### **Opción A: Script Automático (Recomendado) 🌟**

Con reconexión automática y verificación de red:

```bash
# Producción (conecta a Render)
./run_agent_auto.sh prod

# Local (conecta a localhost)
./run_agent_auto.sh local

# Por defecto (usa .env)
./run_agent_auto.sh
```

#### **Opción B: Script Original**

```bash
./run_agent.sh
```

#### **Opción C: Directo con Python**

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar
python agent.py
```

---

## ⚙️ Variables de Entorno

| Variable | Descripción | Ejemplo Producción | Ejemplo Local |
|----------|-------------|-------------------|---------------|
| `DEVICE_ID` | ID del dispositivo (vacío = auto) | `raspi-abc123` | `device-test` |
| `SERVER_WS` | URL del servidor WebSocket | `wss://sims-iot-microservice.onrender.com` | `ws://localhost:8001` |
| `RELAY0_PIN` | Pin GPIO del relé | `17` | `17` |

---

## 🔄 Características de Reconexión

El agente mejorado incluye:

✅ **Verificación de red antes de conectar**
- Verifica conexión a internet (ping a 8.8.8.8)
- Si no hay red, espera 10s y reintenta

✅ **Backoff exponencial**
- Primera desconexión: reintenta en 5s
- Siguientes: 7.5s, 11s, 17s, 25s, 38s, hasta máximo 60s
- Al reconectar exitosamente, resetea a 5s

✅ **Ping/Pong automático**
- Mantiene la conexión activa con ping cada 20s
- Detecta desconexión en 10s (ping_timeout)

✅ **Logs detallados**
- 🔄 Intentando conectar
- ✅ Conexión establecida
- ❌ Error de conexión
- ⚠️ Sin internet

---

## 🧪 Testing

### Test Local (sin Raspberry Pi):

```bash
# Terminal 1: Levantar servidor local
cd ../server
uvicorn main:app --reload --port 8001

# Terminal 2: Ejecutar agente
cd ../agent
./run_agent_auto.sh local
```

### Test Producción (desde cualquier PC):

```bash
# Conectar directamente a Render
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
🔄 Conectando a wss://sims-iot-microservice.onrender.com/ws/device-xxxxx...
✅ ¡CONEXIÓN ESTABLECIDA CON EL SERVIDOR!
```

---

## 🔧 Instalación en Raspberry Pi como Servicio

Para que el agente se ejecute automáticamente al iniciar la Raspberry Pi:

```bash
# Editar el script de instalación
sudo nano install_service.sh

# Asegúrate de que SERVER_WS apunte a Render:
# SERVER_WS=wss://sims-iot-microservice.onrender.com

# Instalar el servicio
sudo ./install_service.sh

# Verificar estado
sudo systemctl status sims-agent

# Ver logs
sudo journalctl -u sims-agent -f
```

---

## 🐛 Solución de Problemas

### Error: "Conexión perdida"

**Causa:** Sin internet o servidor caído

**Solución:**
1. Verifica internet: `ping 8.8.8.8`
2. Verifica servidor: Abre https://sims-iot-microservice.onrender.com/docs
3. El agente reintentará automáticamente cada 5-60s

---

### Error: "WebSocketException"

**Causa:** URL incorrecta o SSL no válido

**Solución:**
1. Para Render, usa `wss://` (con SSL)
2. Para localhost, usa `ws://` (sin SSL)
3. NO incluyas `/api` en la URL del WebSocket

---

### Error: "No module named websockets"

**Causa:** Dependencias no instaladas

**Solución:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📊 Archivos de Configuración

```
agent/
├── agent.py                 # Script principal del agente ⭐
├── .env                     # Configuración activa
├── .env.production          # Configuración para Render (wss://)
├── .env.local              # Configuración para localhost (ws://)
├── run_agent_auto.sh       # Script con reconexión automática ⭐
├── run_agent.sh            # Script original
├── install_service.sh      # Instalar como servicio systemd
└── requirements.txt        # Dependencias Python
```

---

## 🎯 Flujo de Conexión

```
Raspberry Pi (agente)
    ↓ wss:// (WebSocket Secure)
    ↓
Render (sims-iot-microservice)
    ↓ 
MongoDB Atlas (cluster-iot)
    ↑
Render (sims-backend-api)
    ↑ https://
Frontend (Vercel)
```

---

## ✅ Checklist de Deploy

- [ ] `.env` configurado con URL de Render (wss://)
- [ ] Microservicio IoT desplegado en Render
- [ ] Raspberry Pi tiene internet
- [ ] Script `run_agent_auto.sh` ejecutándose
- [ ] Logs muestran "CONEXIÓN ESTABLECIDA"
- [ ] Dashboard web muestra dispositivo "online"

---

## 📞 Comandos Útiles

```bash
# Ver dispositivos conectados en el servidor
curl https://sims-iot-microservice.onrender.com/api/devices | jq

# Test de conexión WebSocket
wscat -c wss://sims-iot-microservice.onrender.com/ws/test-device

# Ver logs del agente
tail -f /var/log/sims-agent.log  # Si está instalado como servicio
```

---

## 🎉 Resultado Esperado

Cuando todo funcione correctamente:

✅ Agente conecta automáticamente al iniciar
✅ Si se pierde internet, reintenta cada 5-60s
✅ Dashboard web muestra dispositivo "online" (verde)
✅ Telemetría se actualiza cada 5s
✅ Comandos desde web funcionan (encender/apagar)

---

**¡Tu agente IoT está listo para producción con reconexión automática!** 🚀
