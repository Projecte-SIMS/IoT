import serial
import pynmea2
import glob
import time

BAUD_RATE = 9600
TIMEOUT = 1
MIN_SATS_FOR_FIX = 4

def find_serial_ports():
    ports = glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*")
    return [p for p in ports if "usb" in p.lower() or "modem" in p.lower()]

def test_gps_port(port):
    try:
        with serial.Serial(port, BAUD_RATE, timeout=TIMEOUT) as ser:
            ser.reset_input_buffer()
            start = time.time()
            while time.time() - start < 5:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if line.startswith("$G"):
                    try:
                        msg = pynmea2.parse(line)
                        if hasattr(msg, "latitude") and hasattr(msg, "longitude"):
                            return True
                    except:
                        pass
    except:
        pass
    return False

def main():
    ports = find_serial_ports()
    if not ports:
        print("No se detectaron puertos serial.")
        return

    gps_port = None
    for p in ports:
        print("Probando:", p)
        if test_gps_port(p):
            gps_port = p
            break

    if not gps_port:
        print("No se detectó GPS. Revisa el UART bridge del Flipper.")
        return

    print("\nGPS detectado en:", gps_port)
    print("Esperando FIX real (cielo abierto)...\n")

    last_status_print = 0

    with serial.Serial(gps_port, BAUD_RATE, timeout=TIMEOUT) as ser:
        try:
            while True:
                line = ser.readline().decode('ascii', errors='ignore').strip()
                if not line.startswith("$G"):
                    continue

                try:
                    msg = pynmea2.parse(line)
                except:
                    continue

                if not hasattr(msg, "latitude"):
                    continue

                lat = msg.latitude
                lon = msg.longitude
                sats = getattr(msg, "num_sats", 0)
                status = getattr(msg, "status", "V")
                speed = getattr(msg, "spd_over_grnd", None)
                course = getattr(msg, "true_course", None)

                try:
                    sats = int(sats)
                except:
                    sats = 0

                # ---- AÚN SIN FIX ----
                if status != "A" or sats < MIN_SATS_FOR_FIX:
                    if time.time() - last_status_print > 2:
                        print(f"Esperando FIX... Satélites: {sats}")
                        last_status_print = time.time()
                    continue

                # ---- FIX REAL ----
                if speed is not None:
                    speed_kmh = float(speed) * 1.852
                else:
                    speed_kmh = None

                print("\n" + "-" * 40)
                print("FIX OK")
                print("Latitud:    ", lat)
                print("Longitud:   ", lon)
                print("Satélites:  ", sats)
                print("Velocidad:  ", f"{speed_kmh:.2f} km/h" if speed_kmh else "N/A")
                print("Rumbo:      ", course)
                print("-" * 40)
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nSaliendo...")

if __name__ == "__main__":
    main()
