try:
    import RPi.GPIO as GPIO
    ES_RASPBERRY = True
except ImportError:
    ES_RASPBERRY = False
    class GPIO:
        BCM = OUT = HIGH = LOW = 0
        def setmode(*a): pass
        def setwarnings(*a): pass
        def setup(*a): pass
        def output(*a): pass
        def input(*a): return 0
        def cleanup(*a): pass
import time

# --- CONFIGURACIÓN GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

RELE = 18
LED = 17
GPIO.setup(RELE, GPIO.OUT)
GPIO.setup(LED, GPIO.OUT)

# Estado inicial: corriente cortada
GPIO.output(RELE, GPIO.LOW)
GPIO.output(LED, GPIO.LOW)

print("Sistema listo")
print("Escribe 'on' para permitir corriente")
print("Escribe 'off' para cortar corriente")
print("Ctrl+C para salir")

try:
    while True:
        comando = input("> ").strip().lower()

        if comando == "on":
            GPIO.output(RELE, GPIO.HIGH)
            GPIO.output(LED, GPIO.HIGH)
            print("Interruptor ACTIVADO (corriente permitida)")

        elif comando == "off":
            GPIO.output(RELE, GPIO.LOW)
            GPIO.output(LED, GPIO.LOW)
            print("Interruptor DESACTIVADO (corriente cortada)")

        else:
            print("Comando no válido (usa on / off)")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nApagando sistema")
    GPIO.output(RELE, GPIO.LOW)
    GPIO.output(LED, GPIO.LOW)
    GPIO.cleanup()