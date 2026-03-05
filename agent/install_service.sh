#!/bin/bash

# Script mejorado para instalar el agente IoT como servicio systemd
# Incluye creación de venv, instalación de dependencias y configuración correcta

set -e  # Salir si hay algún error

# Configuración
SERVICE_NAME="sims-agent"
USER_NAME=$(whoami)
AGENT_DIR=$(pwd)
PYTHON_PATH="$AGENT_DIR/venv/bin/python3"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Instalación del Agente IoT como Servicio Systemd         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "agent.py" ]; then
    echo "❌ Error: No se encuentra agent.py en el directorio actual"
    echo "   Ejecuta este script desde el directorio del agente"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar venv e instalar dependencias
echo "📦 Instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Asegurar que .env existe (usar .env.production si no existe .env)
if [ ! -f ".env" ]; then
    if [ -f ".env.production" ]; then
        echo "📝 Copiando .env.production → .env"
        cp .env.production .env
    else
        echo "❌ Error: No se encuentra .env ni .env.production"
        echo "   Crea un archivo .env con la configuración correcta"
        exit 1
    fi
fi

# Verificar que SERVER_WS esté configurado para producción
if grep -q "localhost" .env; then
    echo "⚠️  ADVERTENCIA: .env contiene 'localhost'"
    echo "   Para producción, debería ser: wss://sims-iot-microservice.onrender.com"
    echo ""
    read -p "¿Continuar de todos modos? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🔧 Creando servicio systemd..."

# Crear el archivo del servicio con configuración mejorada
sudo bash -c "cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=SIMS IoT Agent - Raspberry Pi
Documentation=https://github.com/Projecte-SIMS/IoT
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$AGENT_DIR
EnvironmentFile=$AGENT_DIR/.env
ExecStart=$PYTHON_PATH $AGENT_DIR/agent.py

# Reinicio automático
Restart=always
RestartSec=10

# Logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sims-agent

# Seguridad
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF"

# Recargar systemd
echo "🔄 Recargando systemd..."
sudo systemctl daemon-reload

# Habilitar el servicio para que inicie al arranque
echo "✅ Habilitando inicio automático..."
sudo systemctl enable $SERVICE_NAME

# Iniciar el servicio ahora
echo "🚀 Iniciando el servicio..."
sudo systemctl start $SERVICE_NAME

# Esperar un momento para que inicie
sleep 2

# Verificar estado
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ ¡Servicio instalado e iniciado correctamente!"
    echo ""
    echo "📊 Estado del servicio:"
    sudo systemctl status $SERVICE_NAME --no-pager -l
else
    echo "❌ El servicio se instaló pero NO está corriendo"
    echo ""
    echo "📋 Ver logs para diagnosticar:"
    echo "   sudo journalctl -u $SERVICE_NAME -n 50"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📚 Comandos útiles:"
echo ""
echo "   Ver estado:       sudo systemctl status $SERVICE_NAME"
echo "   Ver logs:         sudo journalctl -u $SERVICE_NAME -f"
echo "   Reiniciar:        sudo systemctl restart $SERVICE_NAME"
echo "   Detener:          sudo systemctl stop $SERVICE_NAME"
echo "   Deshabilitar:     sudo systemctl disable $SERVICE_NAME"
echo "   Eliminar servicio:"
echo "                     sudo systemctl stop $SERVICE_NAME"
echo "                     sudo systemctl disable $SERVICE_NAME"
echo "                     sudo rm /etc/systemd/system/$SERVICE_NAME.service"
echo "                     sudo systemctl daemon-reload"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🔄 El agente se iniciará automáticamente al reiniciar la Raspberry Pi"
echo ""
