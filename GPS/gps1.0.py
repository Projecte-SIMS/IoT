import serial
import pynmea2

# Cambia esto por tu puerto serial
# Windows: "COM3", Linux/Mac: "/dev/ttyUSB0"
SERIAL_PORT = "/dev/tty.usbmodemflip_H0lpl0r1"
BAUD_RATE = 9600

def main():
    # Abrimos puerto serial
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        print("Esperando datos GPS...")

        while True:
            try:
                line = ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$G'):
                    msg = pynmea2.parse(line)
                    # Solo consideramos coordenadas válidas (GGA o RMC)
                    if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                        lat = msg.latitude
                        lon = msg.longitude
                        print(f"Latitud: {lat}, Longitud: {lon}")
            except pynmea2.ParseError:
                continue
            except KeyboardInterrupt:
                print("Saliendo...")
                break

if __name__ == "__main__":
    main()
