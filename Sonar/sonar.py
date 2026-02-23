import time
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import RPi.GPIO as GPIO

# --- GPIO SETUP ---
GPIO.setmode(GPIO.BCM)
TRIG = 23
ECHO = 24

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, False)

time.sleep(2)  # estabilitzar sensor

# --- MATPLOTLIB SETUP ---
plt.ion()
fig, ax = plt.subplots()
ax.set_xlim(-200, 200)
ax.set_ylim(-100, 100)

rect = patches.Rectangle((-200, -100), 400, 200, color='green')
ax.add_patch(rect)

plt.show()

# --- FUNCIO MESURA ---
def mesura_distancia():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    timeout = time.time() + 0.04

    while GPIO.input(ECHO) == 0:
        if time.time() > timeout:
            return None
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1:
        if time.time() > timeout:
            return None
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)

# --- LOOP PRINCIPAL ---
try:
    while True:
        dist = mesura_distancia()

        if dist is None:
            print("Sensor sense resposta")
            rect.set_color('green')

        elif dist < 100:
            print(f"Distància: {dist} cm")
            rect.set_color('red')

        elif dist < 200:
            print(f"Distància: {dist} cm")
            rect.set_color('yellow')

        else:
            print("Fora de rang")
            rect.set_color('green')

        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nAturant programa")
    GPIO.cleanup()
