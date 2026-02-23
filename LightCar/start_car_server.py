from flask import Flask, jsonify
import time

# --------------------------------------------------
# GPIO REAL (Raspberry) o SIMULADO (macOS)
# --------------------------------------------------
import RPi.GPIO as GPIO
ES_RASPBERRY = True


# --------------------------------------------------
# CONFIGURACIÓN GPIO
# --------------------------------------------------
RELE = 18

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RELE, GPIO.OUT)

# Estado inicial: corriente cortada (seguridad)
GPIO.output(RELE, GPIO.LOW)


# --------------------------------------------------
# SERVIDOR FLASK
# --------------------------------------------------
app = Flask(__name__)

@app.route("/on", methods=["POST"])
def activar():
    GPIO.output(RELE, GPIO.HIGH)
    return jsonify({
        "estado": "ON",
        "mensaje": "Paso de corriente ACTIVADO",
        "raspberry": ES_RASPBERRY
    })


@app.route("/off", methods=["POST"])
def desactivar():
    GPIO.output(RELE, GPIO.LOW)
    return jsonify({
        "estado": "OFF",
        "mensaje": "Paso de corriente CORTADO",
        "raspberry": ES_RASPBERRY
    })


@app.route("/status", methods=["GET"])
def estado():
    estado = GPIO.input(RELE)
    return jsonify({
        "estado": "ON" if estado else "OFF",
        "raspberry": ES_RASPBERRY
    })


# --------------------------------------------------
# MAIN
# --------------------------------------------------
if __name__ == "__main__":
    try:
        print("Servidor iniciado")
        print("Modo Raspberry:", ES_RASPBERRY)
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        GPIO.output(RELE, GPIO.LOW)
        GPIO.cleanup()