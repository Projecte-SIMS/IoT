  1. Acciones de Control de Hardware (Actuadores)
  El agente está diseñado principalmente para controlar relés (o cualquier dispositivo conectado a un pin GPIO).
   * Encender (`on`): Activa el pin GPIO configurado (por defecto el 17).
   * Apagar (`off`): Desactiva el pin GPIO configurado.
   * Selección de Relay: Aunque actualmente el servidor solo manda el relay 0, el agente está preparado para manejar múltiples relés si se añaden al
     diccionario RELAYS.


  2. Acciones de Telemetría (Reporte de Estado)
  El agente no solo recibe órdenes, también informa proactivamente:
   * Reporte Periódico: Cada 10 segundos envía su estado actual al servidor.
   * Estado de Relés: Informa si cada relay está actualmente encendido o apagado (esto es lo que ves en la web con los puntos de color).
   * Identificación: Envía su device_name único basado en hardware para que el servidor sepa quién es.


  3. Acciones de Autogestión
   * Auto-identificación: Lee el número de serie de la CPU de la Raspberry Pi para generar un ID único sin intervención humana.
   * Confirmación inmediata (ACK): En cuanto ejecuta un comando (on/off), envía una respuesta inmediata al servidor confirmando que la acción se
     realizó con éxito y el nuevo estado del pin.
   * Reconexión Automática: Si pierde la conexión con el servidor (por ejemplo, si el microservicio se apaga o hay un corte de red), el agente entra
     en un bucle de reintento cada 5 segundos hasta que recupera el enlace.
   * Modo Simulación (Mock): Si ejecutas el agente en un PC (sin pines GPIO), detecta que no hay hardware y entra en modo simulación automáticamente,
     imprimiendo en pantalla Mock Relay ON/OFF en lugar de fallar.