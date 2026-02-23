import serial
import pynmea2
import glob
import time

BAUD_RATE = 9600
TIMEOUT = 1  # segundos

def find_serial_ports():
    ports = glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*")
    return [p for p in ports if "usb" in p.lower() or "modem" in p.lower()]

def test_gps_port(port):
    try:
        with serial.Serial(port, BAUD_RATE, timeout=TIMEOUT) as ser:
            print(f"Probando puerto: {port}")
            ser.reset_input_buffer()
            start_time = time.time()
            while time.time() - start_time < 5:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if line.startswith('$G'):
                    try:
                        msg = pynmea2.parse(line)
                        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                            print(f"GPS detectado en {port}")
                            return port
                    except:
                        pass
    except:
        pass
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
        print("No se detectó GPS.")
        return

    print(f"\nLeyendo datos GPS desde: {gps_port}\n")

    with serial.Serial(gps_port, BAUD_RATE, timeout=TIMEOUT) as ser:
        try:
            while True:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if not line.startswith('$G'):
                    continue

                try:
                    msg = pynmea2.parse(line)
                except:
                    continue

                if not hasattr(msg, 'latitude'):
                    continue

                lat = msg.latitude
                lon = msg.longitude
                sats = getattr(msg, 'num_sats', None)
                speed = getattr(msg, 'spd_over_grnd', None)  # en nudos
                course = getattr(msg, 'true_course', None)
                alt = getattr(msg, 'altitude', None)
                status = getattr(msg, 'status', 'V')

                if speed is not None:
                    speed_kmh = float(speed) * 1.852
                else:
                    speed_kmh = None

                print("-" * 40)
                print("Estado:     ", "FIX" if status == "A" else "NO FIX")
                print("Latitud:    ", lat)
                print("Longitud:   ", lon)
                print("Satélites:  ", sats)
                print("Altitud:    ", f"{alt} m" if alt else "N/A")
                print("Velocidad:  ", f"{speed_kmh:.2f} km/h" if speed_kmh else "0 km/h")
                print("Rumbo:      ", f"{course}°" if course else "N/A")
                print("-" * 40)

                time.sleep(1)

        except KeyboardInterrupt:
            print("\nSaliendo...")

if __name__ == "__main__":
    main()
