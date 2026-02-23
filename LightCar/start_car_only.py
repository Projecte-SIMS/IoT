import sys
import time

# --------------------------------------------------
# GPIO REAL (Raspberry) o SIMULADO
# --------------------------------------------------
try:
    import RPi.GPIO as GPIO
    ES_RASPBERRY = True
except ImportError:
    ES_RASPBERRY = False

    class GPIO:
        BCM = OUT = HIGH = LOW = 0
        @staticmethod
        def setmode(*args): pass
        @staticmethod
        def setwarnings(*args): pass
        @staticmethod
        def setup(*args): pass
        @staticmethod
        def output(*args): pass
        @staticmethod
        def input(*args): return 0
        @staticmethod
        def cleanup(): pass

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
RELE = 18
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RELE, GPIO.OUT)

# --------------------------------------------------
# FUNCIONES
# --------------------------------------------------
def encender():
    GPIO.output(RELE, GPIO.HIGH)
    print("Relé ENCENDIDO")

def apagar():
    GPIO.output(RELE, GPIO.LOW)
    print("Relé APAGADO")

# --------------------------------------------------
# MAIN
# --------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python programa.py on|off")
        sys.exit(1)

    comando = sys.argv[1].lower()

    if comando == "on":
        encender()
    elif comando == "off":
        apagar()
    else:
        print("Comando inválido. Usa: on o off")

    time.sleep(0.5)
    GPIO.cleanup()
