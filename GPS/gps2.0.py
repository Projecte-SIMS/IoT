import serial
import pynmea2

SERIAL_PORT = "/dev/tty.usbmodemflip_H0lpl0r1"
BAUD_RATE = 9600

def main():
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        print("Esperando datos GPS...")
        while True:
            try:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$G'):
                    msg = pynmea2.parse(line)
                    if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                        print(f"Latitud: {msg.latitude}, Longitud: {msg.longitude}")
            except pynmea2.ParseError:
                continue
            except KeyboardInterrupt:
                print("Saliendo...")
                break

if __name__ == "__main__":
    main()
