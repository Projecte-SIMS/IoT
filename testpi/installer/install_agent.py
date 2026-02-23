#!/usr/bin/env python3
"""
Instalador remoto para desplegar el agente en una Raspberry Pi vía SSH.
Requisitos locales: python3 y pip. El script instalará paramiko si no está presente.

Uso: python3 installer/install_agent.py

El script pedirá:
 - Host (IP o dominio)
 - Puerto (opcional, por defecto 22)
 - Usuario
 - Método de autenticación: password o key
 - Si hace falta: contraseña o ruta a la llave privada
 - SERVER_HTTP (URL pública del servidor FastAPI)
 - AGENT_ID (identificador del agente)

Acciones principales que realiza en la Raspberry:
 - Crea carpeta ~/agent
 - Sube los archivos de ./agent (este repositorio)
 - Instala python3, venv si no existen (requiere sudo)
 - Crea venv, instala dependencias
 - Crea servicio systemd /etc/systemd/system/agent.service
 - habilita y arranca el servicio

Advertencia: el script enviará algunos comandos con sudo; si usas autenticación por contraseña se pedirá la contraseña para sudo si es necesario.
"""

import os
import sys
import getpass
import socket
import stat
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    print('paramiko no encontrado, instalando...')
    os.system(f'{sys.executable} -m pip install --user paramiko')
    try:
        import paramiko
    except Exception as e:
        print('No se pudo instalar paramiko:', e)
        sys.exit(1)


def prompt(prompt_text, default=None):
    if default:
        return input(f"{prompt_text} [{default}]: ") or default
    return input(f"{prompt_text}: ")


def recursive_upload(sftp, local_path, remote_path):
    local_path = Path(local_path)
    try:
        sftp.stat(remote_path)
    except IOError:
        sftp.mkdir(remote_path)
    for item in local_path.iterdir():
        remote_item = f"{remote_path}/{item.name}"
        if item.is_dir():
            try:
                sftp.stat(remote_item)
            except IOError:
                sftp.mkdir(remote_item)
            recursive_upload(sftp, item, remote_item)
        else:
            sftp.put(str(item), remote_item)
            # make sure scripts are executable
            if os.access(item, os.X_OK):
                sftp.chmod(remote_item, 0o755)


def run_command(ssh, cmd, sudo_password=None, get_pty=False, timeout=3600):
    # if sudo_password provided and command contains sudo -S it will be fed
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=get_pty, timeout=timeout)
    if sudo_password and 'sudo -S' in cmd:
        try:
            stdin.write(sudo_password + '\n')
            stdin.flush()
        except Exception:
            pass
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def main():
    print('Instalador automático del agente en Raspberry Pi (SSH)')
    host = prompt('Host (IP o dominio)')
    port = int(prompt('Puerto SSH', '22'))
    user = prompt('Usuario')
    auth = prompt('Método de autenticación (password/key)', 'password')
    password = None
    key_path = None
    if auth.lower().startswith('p'):
        password = getpass.getpass('Contraseña SSH: ')
    else:
        key_path = prompt('Ruta a la llave privada (ej: /home/user/.ssh/id_rsa)')
        if not os.path.exists(os.path.expanduser(key_path)):
            print('La llave especificada no existe')
            return
        key_path = os.path.expanduser(key_path)

    server_http = prompt('URL pública del servidor FastAPI (SERVER_HTTP)', 'http://localhost:8000')
    agent_id = prompt('AGENT_ID', 'pi-01')

    # confirm local agent folder exists
    local_agent_dir = Path.cwd() / 'agent'
    if not local_agent_dir.exists():
        print('No se encontró la carpeta ./agent en el repo. Asegúrate de ejecutar el instalador desde la raíz del proyecto.')
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if password:
            ssh.connect(host, port=port, username=user, password=password, timeout=10)
        else:
            ssh.connect(host, port=port, username=user, key_filename=key_path, timeout=10)
    except Exception as e:
        print('Fallo conexión SSH:', e)
        return

    sftp = ssh.open_sftp()
    remote_home_rc, remote_home_out, _ = run_command(ssh, 'echo $HOME')
    remote_home = remote_home_out.strip() or f'/home/{user}'
    remote_agent_dir = f'{remote_home}/agent'

    print('Creando carpeta remota', remote_agent_dir)
    try:
        run_command(ssh, f'mkdir -p {remote_agent_dir}')
    except Exception as e:
        print('Error creando carpeta remota:', e)
        sftp.close()
        ssh.close()
        return

    print('Subiendo archivos...')
    try:
        recursive_upload(sftp, str(local_agent_dir), remote_agent_dir)
    except Exception as e:
        print('Error subiendo archivos:', e)
        sftp.close()
        ssh.close()
        return

    # Ensure python3 and venv exist
    print('Comprobando python3 en la Raspberry...')
    rc, out, err = run_command(ssh, 'python3 --version')
    if rc != 0:
        print('python3 no encontrado. Intentando instalar (puede pedir sudo)...')
        # try apt install with sudo
        install_cmd = 'sudo -S apt-get update && sudo -S apt-get install -y python3 python3-venv python3-pip'
        rc, out, err = run_command(ssh, install_cmd, sudo_password=password, get_pty=True)
        if rc != 0:
            print('No se pudo instalar python3 automaticamente. Salida:', out, err)
            sftp.close()
            ssh.close()
            return

    # create venv
    print('Creando virtualenv...')
    run_command(ssh, f'python3 -m venv {remote_agent_dir}/venv')
    # install requirements
    print('Instalando dependencias pip...')
    pip_path = f'{remote_agent_dir}/venv/bin/pip'
    reqs_path = f'{remote_agent_dir}/requirements.txt'
    rc, out, err = run_command(ssh, f'{pip_path} install --upgrade pip')
    rc, out, err = run_command(ssh, f'{pip_path} install -r {reqs_path}')
    if rc != 0:
        print('Error instalando dependencias:', out, err)
        # continue to try to setup service anyway

    # create systemd service
    service_name = 'agent.service'
    service_remote_path = f'/etc/systemd/system/{service_name}'
    exec_start = f'{remote_agent_dir}/venv/bin/python {remote_agent_dir}/agent.py'
    service_content = f'''[Unit]
Description=Raspberry Agent Service
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={remote_agent_dir}
ExecStart={exec_start}
Restart=on-failure
Environment=SERVER_HTTP={server_http}
Environment=AGENT_ID={agent_id}

[Install]
WantedBy=multi-user.target
'''

    print('Escribiendo servicio systemd en', service_remote_path)
    # write to a temp file in home then move with sudo
    tmp_service = f'{remote_home}/agent.service.tmp'
    try:
        # upload temp file
        with sftp.file(tmp_service, 'w') as f:
            f.write(service_content)
    except Exception as e:
        print('Error escribiendo archivo temporal de servicio:', e)
        sftp.close()
        ssh.close()
        return

    # move to /etc/systemd/system (requires sudo)
    mv_cmd = f'sudo -S mv {tmp_service} {service_remote_path} && sudo -S chown root:root {service_remote_path} && sudo -S chmod 644 {service_remote_path}'
    rc, out, err = run_command(ssh, mv_cmd, sudo_password=password, get_pty=True)
    if rc != 0:
        print('Error moviendo servicio a /etc/systemd/system:', out, err)
        sftp.close()
        ssh.close()
        return

    # reload and enable
    print('Recargando systemd y arrancando servicio...')
    rc, out, err = run_command(ssh, 'sudo -S systemctl daemon-reload', sudo_password=password, get_pty=True)
    rc, out, err = run_command(ssh, f'sudo -S systemctl enable --now {service_name}', sudo_password=password, get_pty=True)

    print('Comprobando estado del servicio...')
    rc, out, err = run_command(ssh, f'systemctl status {service_name} --no-pager')
    print(out)

    print('Instalación finalizada. Si el servicio no está activo revisa los logs con: sudo journalctl -u', service_name)

    sftp.close()
    ssh.close()


if __name__ == '__main__':
    main()
