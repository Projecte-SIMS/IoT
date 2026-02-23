import serial
import pynmea2
import glob
import time

BAUD_RATE = 9600
TIMEOUT = 1  # segundos
TEST_DURATION = 5  # tiempo para probar cada puerto

def find_serial_ports():
    """Detecta puertos serial disponibles en macOS"""
    ports = glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*")
    return [p for p in ports if "usb" in p.lower() or "modem" in p.lower()]

def test_gps_port(port):
    """Prueba si hay datos NMEA en un puerto"""
    try:
        with serial.Serial(port, BAUD_RATE, timeout=TIMEOUT) as ser:
            print(f"Probando puerto: {port}")
            ser.reset_input_buffer()
            start_time = time.time()
            while time.time() - start_time < TEST_DURATION:
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

def parse_gps_data(line):
    """Extrae y retorna datos GPS importantes de una línea NMEA"""
    try:
        msg = pynmea2.parse(line)
        data = {}
        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
            data['lat'] = msg.latitude
            data['lon'] = msg.longitude
        if hasattr(msg, 'spd_over_grnd'):  # velocidad en knots
            data['speed'] = msg.spd_over_grnd
        if hasattr(msg, 'true_course'):  # rumbo en grados
            data['course'] = msg.true_course
        if hasattr(msg, 'num_sats'):
            data['sats'] = msg.num_sats
        if hasattr(msg, 'timestamp'):
            data['time'] = msg.timestamp
        if hasattr(msg, 'datestamp'):
            data['date'] = msg.datestamp
        return data
    except pynmea2.ParseError:
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

    print(f"\nLeyendo datos GPS desde: {gps_port}")
    print("Presiona Ctrl+C para salir.\n")

    with serial.Serial(gps_port, BAUD_RATE, timeout=TIMEOUT) as ser:
        try:
            while True:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$G'):
                    data = parse_gps_data(line)
                    if data:
                        lat = data.get('lat', 'N/A')
                        lon = data.get('lon', 'N/A')
                        sats = data.get('sats', 'N/A')
                        speed = data.get('speed', 'N/A')
                        course = data.get('course', 'N/A')
                        timestamp = data.get('time', 'N/A')
                        date = data.get('date', 'N/A')

                        print(f"Fecha: {date}, Hora: {timestamp}, Lat: {lat}, Lon: {lon}, "
                              f"Satélites: {sats}, Velocidad: {speed} knots, Rumbo: {course}°")
        except KeyboardInterrupt:
            print("\nSaliendo...")

if __name__ == "__main__":
    main()
