# 🔄 Instalación del Agente como Servicio Systemd

## ✅ ¿Por qué instalar como servicio?

El servicio systemd hace que el agente:
- ✅ Se inicie automáticamente al arrancar la Raspberry Pi
- ✅ Se reinicie automáticamente si se cae
- ✅ Funcione en segundo plano (no necesita terminal abierta)
- ✅ Tenga logs centralizados en systemd

---

## 🚀 Instalación (Solo 1 comando)

```bash
cd ~/sims-agent
sudo ./install_service.sh
```

El script automáticamente:
1. ✅ Crea el entorno virtual si no existe
2. ✅ Instala las dependencias
3. ✅ Verifica que `.env` existe (usa `.env.production` si no)
4. ✅ Crea el servicio systemd
5. ✅ Lo habilita para inicio automático
6. ✅ Lo inicia inmediatamente
7. ✅ Verifica que está corriendo

---

## 📊 Verificar Estado

```bash
# Ver estado actual
sudo systemctl status sims-agent

# Debe mostrar:
# Active: active (running)
```

---

## 📝 Ver Logs

```bash
# Logs en tiempo real
sudo journalctl -u sims-agent -f

# Últimas 50 líneas
sudo journalctl -u sims-agent -n 50

# Logs de hoy
sudo journalctl -u sims-agent --since today
```

---

## 🛠️ Comandos Útiles

```bash
# Reiniciar el servicio
sudo systemctl restart sims-agent

# Detener el servicio
sudo systemctl stop sims-agent

# Iniciar el servicio
sudo systemctl start sims-agent

# Ver estado
sudo systemctl status sims-agent

# Verificar si está habilitado para inicio automático
sudo systemctl is-enabled sims-agent
```

---

## 🗑️ Desinstalar el Servicio

```bash
cd ~/sims-agent
sudo ./uninstall_service.sh
```

O manualmente:
```bash
sudo systemctl stop sims-agent
sudo systemctl disable sims-agent
sudo rm /etc/systemd/system/sims-agent.service
sudo systemctl daemon-reload
```

---

## 🔄 Actualizar el Agente

Si actualizas el código del agente:

```bash
cd ~/sims-agent

# Obtener últimos cambios
git pull

# Reinstalar dependencias (por si hay nuevas)
source venv/bin/activate
pip install -r requirements.txt

# Reiniciar el servicio
sudo systemctl restart sims-agent

# Verificar que inició correctamente
sudo systemctl status sims-agent
```

---

## 🐛 Solución de Problemas

### El servicio no inicia

```bash
# Ver logs de error
sudo journalctl -u sims-agent -n 50

# Verificar que el .env existe
cat ~/sims-agent/.env

# Verificar que venv existe y tiene dependencias
ls -la ~/sims-agent/venv/
source ~/sims-agent/venv/bin/activate
pip list | grep websockets
```

### El servicio se cae constantemente

```bash
# Ver últimos errores
sudo journalctl -u sims-agent --since "5 minutes ago"

# Causas comunes:
# 1. Sin internet: El agente esperará 10s y reintentará
# 2. Error en .env: Verifica SERVER_WS
# 3. Dependencias faltantes: Reinstala con pip install -r requirements.txt
```

### No aparece online en el dashboard

```bash
# Verificar que el servicio está corriendo
sudo systemctl status sims-agent

# Ver logs en tiempo real para ver conexión
sudo journalctl -u sims-agent -f

# Debe mostrar:
# ✅ ¡CONEXIÓN ESTABLECIDA CON EL SERVIDOR!

# Si no conecta, verifica:
cat ~/sims-agent/.env | grep SERVER_WS
# Debe ser: wss://sims-iot-microservice.onrender.com
```

---

## ✅ Verificación Completa

Después de instalar, ejecuta esto para verificar todo:

```bash
# 1. Estado del servicio
sudo systemctl status sims-agent

# 2. Ver si está habilitado para inicio automático
sudo systemctl is-enabled sims-agent

# 3. Ver últimos logs
sudo journalctl -u sims-agent -n 20

# 4. Verificar configuración
cat ~/sims-agent/.env

# Todo debería mostrar:
# ✅ Active: active (running)
# ✅ enabled
# ✅ ¡CONEXIÓN ESTABLECIDA CON EL SERVIDOR!
# ✅ SERVER_WS=wss://sims-iot-microservice.onrender.com
```

---

## 🔄 Test de Reinicio

Para verificar que se inicia automáticamente al reiniciar:

```bash
# Reiniciar la Raspberry Pi
sudo reboot

# Esperar 2-3 minutos y reconectar por SSH
ssh pi@tu-raspberry-ip

# Verificar que el servicio está corriendo
sudo systemctl status sims-agent

# Debe mostrar: Active: active (running)
```

---

## 📊 Diferencias: Servicio vs Manual

| Característica | Servicio Systemd | Ejecución Manual |
|----------------|------------------|------------------|
| Inicio automático | ✅ Sí | ❌ No |
| Terminal abierta | ❌ No necesita | ✅ Necesita |
| Reinicio si se cae | ✅ Automático | ❌ Manual |
| Logs centralizados | ✅ journalctl | ❌ Solo stdout |
| Ejecución en background | ✅ Sí | ❌ No (o con nohup) |

---

## 🎯 Recomendación

**Para producción (Raspberry Pi):** Usa el servicio systemd
```bash
sudo ./install_service.sh
```

**Para desarrollo/testing:** Usa ejecución manual
```bash
./run_agent_auto.sh prod
```

---

**¡Listo! El agente se iniciará automáticamente cada vez que reinicies la Raspberry Pi.** 🚀
