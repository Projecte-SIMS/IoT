#!/bin/bash

# Configuración
SERVICE_NAME="raspi-agent"
USER_NAME=$(whoami)
AGENT_DIR=$(pwd)
PYTHON_PATH="$AGENT_DIR/venv/bin/python3"

echo "Instalando el agente como servicio del sistema (systemd)..."

# Crear el archivo del servicio
sudo bash -c "cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Raspberry IoT Agent
After=network.target

[Service]
ExecStart=$PYTHON_PATH $AGENT_DIR/agent.py
WorkingDirectory=$AGENT_DIR
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER_NAME
EnvironmentFile=$AGENT_DIR/.env

[Install]
WantedBy=multi-user.target
EOF"

# Recargar systemd y habilitar el servicio
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "-------------------------------------------------------"
echo "✅ El servicio $SERVICE_NAME ha sido instalado y activado."
echo "🔄 Se iniciará automáticamente al encender la Raspberry."
echo "📜 Puedes ver los logs con: journalctl -u $SERVICE_NAME -f"
echo "-------------------------------------------------------"
