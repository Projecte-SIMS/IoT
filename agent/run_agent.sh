#!/bin/bash
cd "$(dirname "$0")"

# Cargar variables de entorno del archivo .env si existe
if [ -f .env ]; then
  # Extraer variables ignorando comentarios y espacios
  export $(grep -v '^#' .env | xargs)
fi

# Ajustar SERVER_WS a partir de SERVER_URL (para compatibilidad)
if [ ! -z "$SERVER_URL" ]; then
    export SERVER_WS="ws://$SERVER_URL"
fi

echo "Iniciando Agente..."
if [ -z "$DEVICE_ID" ]; then
    echo "DEVICE_ID está vacío. El agente usará el ID de hardware automático."
else
    echo "Usando DEVICE_ID manual: $DEVICE_ID"
fi

# Setup venv
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt --quiet

# Ejecutar el agente
python agent.py
