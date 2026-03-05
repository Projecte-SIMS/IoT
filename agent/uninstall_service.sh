#!/bin/bash

# Script para desinstalar/eliminar el servicio systemd del agente IoT

SERVICE_NAME="sims-agent"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║       Desinstalación del Servicio Systemd del Agente         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar si el servicio existe
if [ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
    echo "⚠️  El servicio $SERVICE_NAME no está instalado"
    exit 0
fi

echo "🛑 Deteniendo el servicio..."
sudo systemctl stop $SERVICE_NAME

echo "❌ Deshabilitando inicio automático..."
sudo systemctl disable $SERVICE_NAME

echo "🗑️  Eliminando archivo del servicio..."
sudo rm /etc/systemd/system/$SERVICE_NAME.service

echo "🔄 Recargando systemd..."
sudo systemctl daemon-reload
sudo systemctl reset-failed

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Servicio $SERVICE_NAME desinstalado correctamente"
echo "════════════════════════════════════════════════════════════════"
echo ""
