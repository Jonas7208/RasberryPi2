import RPi.GPIO as GPIO
import time
import sys
import tty
import termios
import threading
import subprocess
import os
import numpy as np
from PIL import Image

Kamera_Script = "/home/jugendforscht26/RasberryPi2/Kamera.py"
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

MOTOR1_PINS = (17, 22, 23, 24)
MOTOR2_PINS = (10, 9, 25, 11)


FULL_STEP = [
    [1, 0, 1, 0],
    [0, 1, 1, 0],
    [0, 1, 0, 1],
    [1, 0, 0, 1],
]

HALF_STEP = [
    [1, 0, 0, 0],
    [1, 0, 1, 0],
    [0, 0, 1, 0],
    [0, 1, 1, 0],
    [0, 1, 0, 0],
    [0, 1, 0, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1],
]

POSITIONS = {
    0: 0,
    1: 90,
    2: 180,
    3: 270,
    4: 360,
}
Kategorie_zu_Positonen = {
    "cardboard": 1,
    "paper": 1,
    "plastic": 2,
    "metal": 2,
    "glass": 3,
    "trash": 4,
}

SEQUENCES = {
    "full": FULL_STEP,
    "half": HALF_STEP,
}


# --- Hintergrundentfernung aus Kamera.py integriert ---

def remove_background(input_path: str, output_path: str, threshold: int = 230) -> bool:
    """Entfernt weißen Hintergrund aus einem Bild und speichert es mit Transparenz."""
    try:
        print("Entferne weißen Hintergrund...")
        img = Image.open(input_path).convert("RGBA")
        data = np.array(img)

        r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]

        white_mask = (r > threshold) & (g > threshold) & (b > threshold)
        data[white_mask] = [255, 255, 255, 0]

        result = Image.fromarray(data)
        result.save(output_path)
        print(f"Hintergrund entfernt. Gespeichert als: {output_path}")
        return True

    except Exception as e:
        print(f"Fehler bei Hintergrundentfernung: {e}")
        return False


# --- StepperMotor-Klasse ---

class StepperMotor:

    def __init__(self, pins, name="Motor", steps_per_rev=200, gear_ratio=1.0):
        self.pins = pins
        self.name = name
        self.steps_per_rev = steps_per_rev
        self.gear_ratio = gear_ratio
        self.current_position = 0.0

        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0)

    def _set_step(self, step):
        for pin, value in zip(self.pins, step):
            GPIO.output(pin, value)

    def _get_sequence(self, mode):
        return SEQUENCES.get(mode, FULL_STEP)

    def rotate_steps(self, steps, delay=0.005, clockwise=True, mode="full"):
        sequence = self._get_sequence(mode)
        seq_len = len(sequence)

        for i in range(steps):
            index = i % seq_len
            if not clockwise:
                index = seq_len - 1 - index
            self._set_step(sequence[index])
            time.sleep(delay)

        degrees = (steps / (self.steps_per_rev * self.gear_ratio)) * 360.0
        direction = 1 if clockwise else -1
        self.current_position = (self.current_position + direction * degrees) % 360

    def move_to_position(self, position_num, delay=0.005, mode="full"):
        if position_num not in POSITIONS:
            return

        target = POSITIONS[position_num]
        diff = target - self.current_position

        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360

        clockwise = diff >= 0
        degrees_to_move = abs(diff)

        multiplier = 2 if mode == "half" else 1
        steps = int((degrees_to_move / 360.0) * self.steps_per_rev * multiplier * self.gear_ratio)

        if steps > 0:
            self.rotate_steps(steps, delay, clockwise, mode)

        self.current_position = target

    def move_to_home(self, delay=0.005, mode="full"):
        self.move_to_position(0, delay, mode)

    def stop(self):
        for pin in self.pins:
            GPIO.output(pin, 0)

    def hold(self):
        self._set_step(FULL_STEP[0])

    def reset_position(self):
        self.current_position = 0.0


def move_motors_simultaneously(motors, action, *args, **kwargs):
    threads = []
    for motor in motors:
        method = getattr(motor, action)
        t = threading.Thread(target=method, args=args, kwargs=kwargs)
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    for motor in motors:
        motor.stop()


def get_char():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def Kamera_erkennung():
    """Startet die Kamera, entfernt den Hintergrund und führt die CNN-Erkennung durch."""
    print("Starte Kamera und Erkennung...")

    result = subprocess.run(
        [sys.executable, Kamera_Script],
        capture_output=True,
        text=True
    )

    print(f"Kamera-Ausgabe:\n{result.stdout}")

    if result.returncode != 0:
        print(f"Fehler bei Kamera/CNN:\n{result.stderr}")
        return None

    kategorie = None
    bildpfad = None

    for line in result.stdout.splitlines():
        if line.startswith("Kategorie:"):
            kategorie = line.split(":", 1)[1].strip().lower()
        elif line.startswith("Bild:"):
            bildpfad = line.split(":", 1)[1].strip()

    if kategorie:
        print(f"Kategorie erkannt: {kategorie}")

    # Hintergrundentfernung auf das aufgenommene Bild anwenden
    if bildpfad and os.path.exists(bildpfad):
        no_bg_path = os.path.splitext(bildpfad)[0] + "_no_bg.png"
        if remove_background(bildpfad, no_bg_path):
            print(f"Bild ohne Hintergrund: {no_bg_path}")
            # Originalbild aufräumen
            try:
                os.remove(bildpfad)
            except FileNotFoundError:
                pass
    elif bildpfad:
        print(f"Bilddatei nicht gefunden: {bildpfad}")

    return kategorie


if __name__ == "__main__":
    motor1 = StepperMotor(MOTOR1_PINS, "Motor 1", steps_per_rev=200, gear_ratio=2.0)
    motor2 = StepperMotor(MOTOR2_PINS, "Motor 2", steps_per_rev=200, gear_ratio=2.0)
    motors = [motor1, motor2]

    delay = 0.005

    print("k=Kamera,"
          "0-4=Positionen,"
          "h=Home,")

    try:
        while True:
            cmd = get_char().lower()
            if cmd == "k":
                kategorie = Kamera_erkennung()
                if kategorie:
                    position = Kategorie_zu_Positonen.get(kategorie, 0)
                    print(f" '{kategorie}' → Position {position}")
                    move_motors_simultaneously(motors, "move_to_position", position, delay)
                    print("Warte 1 Sekunde...")
                    time.sleep(1)
                    print("Auswurf...")
                    motor1.rotate_steps(int(200 * motor1.gear_ratio), 0.005, True)
                    time.sleep(1)
                    print("Fahre zurück zur Home-Position...")
                    move_motors_simultaneously(motors, "move_to_home", delay)
                    print("Fertig!")
                else:
                    print("Keine Kategorie erkannt, Motor bleibt stehen.")

            elif cmd in "01234":
                pos = int(cmd)
                move_motors_simultaneously(motors, "move_to_position", pos, delay)
                time.sleep(1)
                motor2.hold()
                motor1.rotate_steps(int(200 * motor1.gear_ratio), 0.005, True)
                motor2.stop()
                time.sleep(1)

                move_motors_simultaneously(motors, "move_to_home", delay)

            elif cmd == "h":
                move_motors_simultaneously(motors, "move_to_home", delay)

            elif cmd == "r":
                for m in motors:
                    m.reset_position()

            elif cmd == "s":
                for m in motors:
                    m.stop()

            elif cmd == "p":
                for m in motors:
                    print(f"  {m.name}: {m.current_position:.1f}°")

            elif cmd == "+":
                delay = max(0.003, delay - 0.001)

            elif cmd == "-":
                delay = min(0.020, delay + 0.001)

            elif cmd in ("q", "\x03"):
                break

    except KeyboardInterrupt:
        pass

    finally:
        for m in motors:
            m.stop()
    GPIO.cleanup()