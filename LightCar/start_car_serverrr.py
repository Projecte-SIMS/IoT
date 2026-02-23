from flask import Flask, jsonify
import RPi.GPIO as GPIO
import time

# --- CONFIG GPIO ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

RELE = 18
GPIO.setup(RELE, GPIO.OUT)

# Estado inicial: CORTE DE CORRIENTE
GPIO.output(RELE, GPIO.LOW)

# --- FLASK ---
app = Flask(__name__)

@app.route("/on", methods=["POST"])
def activar():
    GPIO.output(RELE, GPIO.HIGH)
    return jsonify({
        "estado": "ON",
        "mensaje": "Paso de corriente ACTIVADO"
    })

@app.route("/off", methods=["POST"])
def desactivar():
    GPIO.output(RELE, GPIO.LOW)
    return jsonify({
        "estado": "OFF",
        "mensaje": "Paso de corriente CORTADO"
    })

@app.route("/status", methods=["GET"])
def estado():
    estado = GPIO.input(RELE)
    return jsonify({
        "estado": "ON" if estado else "OFF"
    })

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        GPIO.output(RELE, GPIO.LOW)
        GPIO.cleanup()