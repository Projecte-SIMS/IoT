# 🚀 Quick Start - Agente IoT en Raspberry Pi

## ✅ Resumen

Usa el script `run_agent_auto.sh` para conectar automáticamente a Render con reconexión automática.

---

## 📦 Instalación en Raspberry Pi

### 1. Copiar archivos desde tu Mac

```bash
# Desde tu Mac, ejecuta:
scp -r /Users/ganso/Desktop/SIMS_SPRINT4/Raspberry_py/agent/ pi@192.168.1.100:~/sims-agent/

# Reemplaza 192.168.1.100 con la IP de tu Raspberry Pi
```

---

### 2. Conectar a la Raspberry Pi

```bash
ssh pi@192.168.1.100
cd ~/sims-agent
```

---

### 3. Ejecutar el agente

**Opción A: Modo producción (conecta a Render) - RECOMENDADO**

```bash
chmod +x run_agent_auto.sh
./run_agent_auto.sh prod
```

Deberías ver:
```
🌐 Modo PRODUCCIÓN: Conectando a Render (wss://)
✅ Configuración cargada desde: .env.production
📊 CONFIGURACIÓN DEL AGENTE:
   • Device ID: [Auto-generado]
   • Servidor:  wss://sims-iot-microservice.onrender.com
🚀 Iniciando agente IoT...
🔄 Conectando a wss://sims-iot-microservice.onrender.com/ws/device-xxxxx...
✅ ¡CONEXIÓN ESTABLECIDA CON EL SERVIDOR!
```

**Opción B: Modo local (para testing)**

```bash
./run_agent_auto.sh local
```

---

### 4. Verificar en el Dashboard Web

1. Abre: https://frontend-nine-orcin-waqisje40z.vercel.app
2. Login: `admin@sims.com` / `password`
3. Ve a: Admin → Dispositivos IoT
4. Click: "Actualizar"
5. ✅ Deberías ver tu dispositivo **"Online"** (verde)

---

## 🔄 Instalar como Servicio (Opcional)

Para que se ejecute automáticamente al iniciar la Raspberry Pi:

```bash
sudo ./install_service.sh
```

Comandos útiles:
```bash
sudo systemctl status sims-agent     # Ver estado
sudo systemctl start sims-agent      # Iniciar
sudo systemctl stop sims-agent       # Detener
sudo journalctl -u sims-agent -f     # Ver logs en tiempo real
```

---

## 🛑 Detener el Agente

```bash
# Si está corriendo en terminal:
Ctrl + C

# Si está como servicio:
sudo systemctl stop sims-agent
```

---

## 📊 Configuración de URLs

| Entorno | Comando | URL |
|---------|---------|-----|
| **Producción** | `./run_agent_auto.sh prod` | `wss://sims-iot-microservice.onrender.com` |
| **Local** | `./run_agent_auto.sh local` | `ws://localhost:8001` |

---

## ✅ El agente automáticamente:

- 🌐 Verifica internet antes de conectar
- 🔄 Se reconecta cada 5-60s si se cae
- 📡 Mantiene la conexión viva con ping/pong
- 📊 Envía telemetría cada 5 segundos
- 🔌 Recibe comandos remotos (on/off)

---

## 📖 Documentación Completa

- `README_AGENT.md` - Guía completa del agente
- `DEPLOY_AGENT.md` - Guía de deploy detallada
- `.env.production` - Config para Render
- `.env.local` - Config para localhost

---

**¡Listo! Tu agente IoT se conectará automáticamente a Render desde la Raspberry Pi.** 🚀
