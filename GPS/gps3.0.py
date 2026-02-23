import serial
import pynmea2
import glob
import time

BAUD_RATE = 9600
TIMEOUT = 1  # segundos
RETRY_SECONDS = 5

def find_serial_ports():
    """Detecta puertos serial disponibles en macOS"""
    ports = glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*")
    # Filtramos los puertos comunes de USB-UART
    return [p for p in ports if "usb" in p.lower() or "modem" in p.lower()]

def test_gps_port(port):
    """Intenta leer datos NMEA de un puerto"""
    try:
        with serial.Serial(port, BAUD_RATE, timeout=TIMEOUT) as ser:
            print(f"Probando puerto: {port}")
            ser.reset_input_buffer()
            start_time = time.time()
            while time.time() - start_time < 5:  # probar 5 segundos
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$G'):
                    try:
                        msg = pynmea2.parse(line)
                        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                            print(f"GPS detectado en {port}")
                            return port
                    except pynmea2.ParseError:
                        continue
    except Exception as e:
        print(f"No se pudo abrir {port}: {e}")
    return None

def main():
    ports = find_serial_ports()
    if not ports:
        print("No se detectaron puertos serial.")
        return

    gps_port = None
    for port in ports:
        gps_port = test_gps_port(port)
        if gps_port:
            break

    if not gps_port:
        print("No se detectó GPS. Verifica conexiones y modo UART passthrough del Flipper.")
        return

    # Si llegamos aquí, GPS encontrado
    print(f"Leyendo datos GPS desde: {gps_port}")
    with serial.Serial(gps_port, BAUD_RATE, timeout=TIMEOUT) as ser:
        try:
            while True:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$G'):
                    try:
                        msg = pynmea2.parse(line)
                        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                            print(f"Latitud: {msg.latitude}, Longitud: {msg.longitude}")
                    except pynmea2.ParseError:
                        continue
        except KeyboardInterrupt:
            print("Saliendo...")

if __name__ == "__main__":
    main()
