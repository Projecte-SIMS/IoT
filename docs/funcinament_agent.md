# Funcionamiento del Agente IoT en Raspberry Pi

Este documento describe los procesos internos y las capacidades del agente desarrollado en Python que se ejecuta en los dispositivos Raspberry Pi de la flota.

---

## 1. Acciones de Control de Hardware (Actuadores)

El agente está diseñado para controlar relés o cualquier dispositivo conectado a los pines GPIO de la Raspberry Pi mediante la librería `gpiozero`.

- **Encender (on):** Activa el pin GPIO configurado (por defecto el pin 17). Esto permite cerrar el circuito del relé para, por ejemplo, permitir el arranque del vehículo.
- **Apagar (off):** Desactiva el pin GPIO configurado, abriendo el circuito del relé.
- **Selección de Relé:** Aunque actualmente el servidor opera principalmente sobre el relé 0, el agente está preparado para gestionar múltiples actuadores si se añaden al diccionario de configuración correspondiente.
- **Reinicio (reboot):** El agente tiene la capacidad de ejecutar un comando de reinicio del sistema operativo si recibe la orden correspondiente desde el servidor.

---

## 2. Acciones de Telemetría (Reporte de Estado)

El agente no solo recibe órdenes, sino que informa de manera proactiva sobre el estado del hardware y el entorno:

- **Reporte Periódico:** Cada 5 segundos, el agente envía un paquete de datos completo al servidor FastAPI.
- **Estado de Relés:** Informa en tiempo real si cada relé está actualmente activado o desactivado. Esta información es la que se visualiza en el panel de control web mediante indicadores de estado.
- **Datos de Sensores:** 
    - **GPS:** Posición exacta (latitud y longitud), velocidad actual y altitud.
    - **Motor:** Monitorización simulada o real de las revoluciones por minuto (RPM) y la temperatura del motor.
    - **Batería:** Reporte del voltaje actual de la batería del vehículo.
- **Identificación Única:** Envía su identificador de hardware único en cada mensaje para que el servidor pueda asociar los datos al vehículo correcto.

---

## 3. Acciones de Autogestión y Resiliencia

El agente incluye mecanismos para garantizar su funcionamiento autónomo y la recuperación ante fallos:

- **Auto-identificación:** El script intenta leer el número de serie de la CPU de la Raspberry Pi para generar un identificador único de forma automática, facilitando el despliegue masivo sin intervención manual.
- **Confirmación Inmediata (ACK):** Tras ejecutar un comando (encendido o apagado), el agente envía una respuesta inmediata de confirmación al servidor indicando el nuevo estado del hardware.
- **Reconexión Automática:** En caso de pérdida de conexión con el servidor (por problemas de red o reinicio del microservicio), el agente entra en un bucle de reintento automático cada 5 segundos hasta restablecer el enlace.
- **Modo de Simulación (Mock):** Si el agente se ejecuta en un entorno sin pines GPIO (como un ordenador personal para pruebas), detecta automáticamente la ausencia de hardware y activa un modo de simulación. En este modo, las acciones se registran en el log del sistema sin provocar errores de ejecución.
- **Seguridad en el Arranque:** El agente puede configurarse como un servicio de `systemd` para asegurar que se inicie automáticamente al encender la Raspberry Pi y que se reinicie en caso de fallo crítico del proceso.
