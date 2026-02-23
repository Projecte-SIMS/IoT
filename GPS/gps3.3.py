import serial
import pynmea2
import glob
import time
import os
import math

BAUD_RATE = 9600
TIMEOUT = 1
RADAR_RADIUS = 10  # tamaño del radar en caracteres

def find_serial_ports():
    ports = glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*")
    return [p for p in ports if "usb" in p.lower() or "modem" in p.lower()]

def test_gps_port(port):
    try:
        with serial.Serial(port, BAUD_RATE, timeout=TIMEOUT) as ser:
            ser.reset_input_buffer()
            start_time = time.time()
            while time.time() - start_time < 5:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$G'):
                    try:
                        msg = pynmea2.parse(line)
                        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                            return port
                    except pynmea2.ParseError:
                        continue
    except Exception:
        return None
    return None

def parse_gps_data(line):
    try:
        msg = pynmea2.parse(line)
        data = {}
        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
            data['lat'] = msg.latitude
            data['lon'] = msg.longitude
        if hasattr(msg, 'num_sats'):
            data['sats'] = msg.num_sats
        if hasattr(msg, 'spd_over_grnd'):
            data['speed_knots'] = msg.spd_over_grnd
            data['speed_kmh'] = msg.spd_over_grnd * 1.852
        if hasattr(msg, 'true_course'):
            data['course'] = msg.true_course
        return data
    except pynmea2.ParseError:
        return None

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_radar(lat, lon, origin_lat, origin_lon, sats, speed):
    """Dibuja un radar con la posición relativa al punto de origen"""
    dx = (lon - origin_lon) * 111000 * math.cos(math.radians(origin_lat))  # metros aprox
    dy = (lat - origin_lat) * 111000  # metros aprox

    # Escalar a la cuadrícula del radar
    scale = RADAR_RADIUS / 50  # 50 metros ≈ radio del radar
    x = int(dx * scale)
    y = int(dy * scale)

    size = RADAR_RADIUS * 2 + 1
    grid = [[' ' for _ in range(size)] for _ in range(size)]

    for i in range(size):
        for j in range(size):
            # Dibujar círculo aproximado
            if math.isclose(math.hypot(i - RADAR_RADIUS, j - RADAR_RADIUS), RADAR_RADIUS, abs_tol=0.5):
                grid[i][j] = '.'

    # Posición del GPS dentro del radar
    rx = RADAR_RADIUS + x
    ry = RADAR_RADIUS - y  # invertir eje Y
    if 0 <= rx < size and 0 <= ry < size:
        grid[ry][rx] = 'O'  # marcador GPS

    # Mostrar radar en consola
    for row in grid:
        print(''.join(row))
    print(f"Satélites: {sats}, Velocidad: {speed.get('speed_kmh','N/A'):.1f} km/h")

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

    print(f"GPS detectado en puerto: {gps_port}")
    print("Presiona Ctrl+C para salir.\n")

    origin_lat = None
    origin_lon = None

    with serial.Serial(gps_port, BAUD_RATE, timeout=TIMEOUT) as ser:
        try:
            while True:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$G'):
                    data = parse_gps_data(line)
                    if data and 'lat' in data and 'lon' in data:
                        if origin_lat is None:
                            origin_lat = data['lat']
                            origin_lon = data['lon']
                        clear_console()
                        print_radar(data['lat'], data['lon'], origin_lat, origin_lon,
                                    data.get('sats', 0), data)
                        time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nSaliendo...")

if __name__ == "__main__":
    main()
