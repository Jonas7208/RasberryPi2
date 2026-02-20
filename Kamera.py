from picamera2 import Picamera2
from datetime import datetime
import time
import subprocess
import sys
import os
from rembg import remove
from PIL import Image
import io

PYTHON_310 = "/home/jugendforscht26/env/bin/python3.10"
CNN_SCRIPT = "/home/jugendforscht26/RasberryPi2/CNN.py"


def remove_background(input_path: str, output_path: str) -> bool:
    """
    Entfernt den Hintergrund eines Bildes und speichert das Ergebnis als PNG.
    Gibt True zurück bei Erfolg, False bei Fehler.
    """
    try:
        print("Entferne Hintergrund...")
        with open(input_path, "rb") as f:
            input_data = f.read()

        output_data = remove(input_data)

        with open(output_path, "wb") as f:
            f.write(output_data)

        print(f"Hintergrund entfernt. Gespeichert als: {output_path}")
        return True

    except Exception as e:
        print(f"Fehler bei Hintergrundentfernung: {e}")
        return False


def main():
    picam2 = Picamera2()
    picam2.configure(picam2.create_still_configuration())

    print("Starte Kamera...")
    picam2.start()
    time.sleep(2)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"still_{timestamp}.jpg"
    filename_no_bg = f"still_{timestamp}_no_bg.png"

    print(f"Nehme Foto auf: {filename}")
    picam2.capture_file(filename)
    picam2.stop()

    # Hintergrund entfernen
    bg_removed = remove_background(filename, filename_no_bg)

    # Inferenz mit dem Bild ohne Hintergrund (falls erfolgreich), sonst Original
    inference_input = filename_no_bg if bg_removed else filename

    print(f"Starte Inferenz mit: {inference_input} (Python 3.10)...")
    result = subprocess.run(
        [PYTHON_310, CNN_SCRIPT, inference_input],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print("Fehler bei Inferenz:")
        print(result.stderr)

    # Aufräumen: beide Dateien löschen
    for f in [filename, filename_no_bg]:
        try:
            os.remove(f)
            print(f"Datei '{f}' wurde erfolgreich gelöscht.")
        except FileNotFoundError:
            print(f"Datei '{f}' nicht gefunden.")


if __name__ == "__main__":
    main()