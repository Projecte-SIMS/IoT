import serial
import pynmea2
import glob
import time
import os

BAUD_RATE = 9600
TIMEOUT = 1
TEST_DURATION = 5

def find_serial_ports():
    ports = glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*")
    return [p for p in ports if "usb" in p.lower() or "modem" in p.lower()]

def test_gps_port(port):
    try:
        with serial.Serial(port, BAUD_RATE, timeout=TIMEOUT) as ser:
            ser.reset_input_buffer()
            start_time = time.time()
            while time.time() - start_time < TEST_DURATION:
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
        if hasattr(msg, 'timestamp'):
            data['time'] = msg.timestamp
        if hasattr(msg, 'datestamp'):
            data['date'] = msg.datestamp
        return data
    except pynmea2.ParseError:
        return None

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

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

    with serial.Serial(gps_port, BAUD_RATE, timeout=TIMEOUT) as ser:
        try:
            while True:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$G'):
                    data = parse_gps_data(line)
                    if data:
                        clear_console()
                        print("====== DASHBOARD GPS ======")
                        print(f"Fecha:       {data.get('date', 'N/A')}")
                        print(f"Hora:        {data.get('time', 'N/A')}")
                        print(f"Latitud:     {data.get('lat', 'N/A')}")
                        print(f"Longitud:    {data.get('lon', 'N/A')}")
                        print(f"Satélites:   {data.get('sats', 'N/A')}")
                        print(f"Velocidad:   {data.get('speed_knots', 'N/A')} kn / {data.get('speed_kmh', 'N/A'):.1f} km/h")
                        print(f"Rumbo:       {data.get('course', 'N/A')}°")
                        print("============================")
                        time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nSaliendo...")

if __name__ == "__main__":
    main()
