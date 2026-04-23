#!/usr/bin/env python3
"""
SIMS Fleet Manager
Herramienta para el despliegue y actualización masiva de agentes IoT en Raspberry Pi.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

# Configuración por defecto
DEFAULT_INVENTORY = "inventory.json"
AGENT_DIR = Path(__file__).parent / "agent"

def run_command(cmd, host=None):
    """Ejecuta un comando localmente o vía SSH"""
    if host:
        full_cmd = ["ssh", "-o", "ConnectTimeout=5", host, cmd]
    else:
        full_cmd = cmd if isinstance(cmd, list) else cmd.split()
    
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando en {host or 'local'}: {e.stderr}")
        return None

def copy_to_host(local_path, remote_path, host):
    """Copia archivos vía SCP"""
    try:
        subprocess.run(["scp", "-r", str(local_path), f"{host}:{remote_path}"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al copiar a {host}: {e.stderr}")
        return False

def deploy_agent(device):
    host = f"{device['user']}@{device['ip']}"
    print(f"\n🚀 Desplegando en {device['id']} ({host})...")
    
    # 1. Preparar directorio remoto
    run_command(f"mkdir -p ~/sims-iot", host)
    
    # 2. Copiar archivos del agente (excluyendo venv y __pycache__)
    print(f"📦 Copiando código...")
    # Creamos un temporal sin basura para copiar
    tmp_deploy = Path("/tmp/sims_deploy")
    tmp_deploy.mkdir(exist_ok=True)
    subprocess.run(f"rsync -av --exclude 'venv' --exclude '__pycache__' {AGENT_DIR}/ {tmp_deploy}/", shell=True, capture_output=True)
    
    # Crear .env específico para este dispositivo
    env_content = [
        f"DEVICE_ID={device['id']}",
        f"TENANT_ID={device.get('tenant_id', 'default')}",
        f"SERVER_WS={device.get('server_ws', 'wss://sims-iot-microservice.onrender.com')}",
        f"IOT_API_KEY={device.get('api_key', 'MACMECMIC')}",
        f"RELAY0_PIN={device.get('relay_pin', 17)}"
    ]
    with open(tmp_deploy / ".env", "w") as f:
        f.write("\n".join(env_content))
    
    if not copy_to_host(f"{tmp_deploy}/", "~/sims-iot/", host):
        return False

    # 3. Iniciar con Docker o Systemd
    if device.get("use_docker", True):
        print("🐳 Iniciando con Docker...")
        run_command("cd ~/sims-iot && docker compose up -d --build", host)
    else:
        print("🔧 Iniciando con Systemd...")
        run_command("cd ~/sims-iot && chmod +x install_service.sh && ./install_service.sh", host)
    
    print(f"✅ Despliegue completado en {device['id']}")
    return True

def get_local_hw_id():
    """Detecta ID de hardware localmente (Raspberry Serial o UUID)"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    return f"raspi-{line.split(':')[1].strip()}"
    except: pass
    import uuid
    return f"device-{hex(uuid.getnode())[2:]}"

def auto_deploy_local():
    """Despliegue automático en la máquina actual detectando hardware"""
    hw_id = get_local_hw_id()
    print(f"🕵️ Detectado hardware: {hw_id}")
    
    device = {
        "id": hw_id,
        "ip": "localhost",
        "user": os.getlogin(),
        "tenant_id": "default",
        "api_key": "MACMECMIC",
        "use_docker": os.path.exists("/var/run/docker.sock")
    }
    
    # 1. Crear .env local
    env_content = [
        f"DEVICE_ID={device['id']}",
        f"TENANT_ID={device['tenant_id']}",
        f"SERVER_WS=ws://localhost:8001",
        f"IOT_API_KEY={device['api_key']}",
        f"RELAY0_PIN=17"
    ]
    
    with open(AGENT_DIR / ".env", "w") as f:
        f.write("\n".join(env_content))
    
    print(f"📝 Configurado .env para {hw_id}")
    
    # 2. Iniciar
    if device["use_docker"]:
        print("🐳 Iniciando con Docker...")
        subprocess.run(["docker", "compose", "-f", str(AGENT_DIR / "docker-compose.yml"), "up", "-d", "--build"])
    else:
        print("🔧 Iniciando con Systemd...")
        subprocess.run(["bash", str(AGENT_DIR / "install_service.sh")], cwd=AGENT_DIR)

def main():
    parser = argparse.ArgumentParser(description="SIMS Fleet Manager")
    parser.add_argument("action", choices=["deploy", "status", "update-keys", "reboot", "auto-deploy"], help="Acción a realizar")
    parser.add_argument("--inventory", default=DEFAULT_INVENTORY, help="Archivo de inventario JSON")
    parser.add_argument("--id", help="Filtrar por ID de dispositivo específico")
    
    args = parser.parse_args()

    if args.action == "auto-deploy":
        auto_deploy_local()
        return

    if not os.path.exists(args.inventory):
        # Crear inventario de ejemplo si no existe
        example_inventory = [
            {
                "id": "AUTO-001",
                "ip": "192.168.1.100",
                "user": "pi",
                "tenant_id": "feetly",
                "api_key": "NUEVA_KEY_SEGURA",
                "use_docker": True
            }
        ]
        with open(args.inventory, "w") as f:
            json.dump(example_inventory, f, indent=4)
        print(f"📝 Se ha creado un archivo '{args.inventory}' de ejemplo. Edítalo con tus Raspberries.")
        return

    with open(args.inventory, "r") as f:
        devices = json.load(f)

    if args.id:
        devices = [d for d in devices if d['id'] == args.id]

    for device in devices:
        if args.action == "deploy":
            deploy_agent(device)
        elif args.action == "status":
            host = f"{device['user']}@{device['ip']}"
            res = run_command("docker ps --filter name=sims-iot-agent --format '{{.Status}}' || systemctl is-active sims-agent", host)
            print(f"📊 {device['id']}: {res or 'OFFLINE'}")
        elif args.action == "reboot":
            host = f"{device['user']}@{device['ip']}"
            print(f"🔄 Reiniciando {device['id']}...")
            run_command("sudo reboot", host)
        elif args.action == "update-keys":
            print(f"🔑 Actualizando keys en {device['id']}...")
            host = f"{device['user']}@{device['ip']}"
            run_command(f"sed -i 's/IOT_API_KEY=.*/IOT_API_KEY={device['api_key']}/' ~/sims-iot/.env", host)
            run_command("cd ~/sims-iot && (docker compose restart || sudo systemctl restart sims-agent)", host)

if __name__ == "__main__":
    main()
