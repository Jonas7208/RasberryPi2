from picamera2 import Picamera2
from datetime import datetime
import time
import subprocess
import sys
import os

PYTHON_310 = "/home/jugendforscht26/env/bin/python3.10"
CNN_SCRIPT = "/home/jugendforscht26/RasberryPi2/CNN.py"


def main():
    picam2 = Picamera2()
    picam2.configure(picam2.create_still_configuration())

    print("Starte Kamera...")
    picam2.start()
    time.sleep(2)

    filename = f"still_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
    print(f"Nehme Foto auf: {filename}")
    picam2.capture_file(filename)
    picam2.stop()

    print("Starte Inferenz (Python 3.10)...")

    result = subprocess.run(
        [PYTHON_310, CNN_SCRIPT, filename],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print("Fehler bei Inferenz:")
        print(result.stderr)

    try:
        os.remove(filename)
        print(f"Datei '{filename}' wurde erfolgreich gelöscht.")
    except FileNotFoundError:
        print(f"Datei '{filename}' nicht gefunden.")


if __name__ == "__main__":
    main()
