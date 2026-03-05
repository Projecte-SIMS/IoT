#!/bin/bash

# Script mejorado para ejecutar el agente con reconexión automática
cd "$(dirname "$0")"

# Determinar qué archivo .env usar
ENV_FILE=".env"

# Si se pasa un argumento, usar ese perfil
if [ "$1" = "prod" ] || [ "$1" = "production" ]; then
    if [ -f .env.production ]; then
        ENV_FILE=".env.production"
        echo "🌐 Modo PRODUCCIÓN: Conectando a Render (wss://)"
    fi
elif [ "$1" = "local" ] || [ "$1" = "dev" ]; then
    if [ -f .env.local ]; then
        ENV_FILE=".env.local"
        echo "🏠 Modo LOCAL: Conectando a localhost (ws://)"
    fi
else
    echo "📍 Usando configuración por defecto (.env)"
fi

# Cargar variables de entorno
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
    echo "✅ Configuración cargada desde: $ENV_FILE"
else
    echo "⚠️ Archivo $ENV_FILE no encontrado, usando valores por defecto"
fi

# Mostrar configuración
echo ""
echo "📊 CONFIGURACIÓN DEL AGENTE:"
echo "   • Device ID: ${DEVICE_ID:-[Auto-generado]}"
echo "   • Servidor:  $SERVER_WS"
echo "   • Relay Pin: ${RELAY0_PIN:-17}"
echo ""

# Setup venv si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar venv
source venv/bin/activate

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt --quiet

# Ejecutar el agente con reconexión automática
echo ""
echo "🚀 Iniciando agente IoT..."
echo "   (Presiona Ctrl+C para detener)"
echo ""

while true; do
    python agent.py
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Agente terminó correctamente"
        break
    else
        echo ""
        echo "⚠️ Agente detenido (código: $EXIT_CODE)"
        echo "🔄 Reiniciando en 5 segundos..."
        echo "   (Presiona Ctrl+C para cancelar)"
        sleep 5
    fi
done
