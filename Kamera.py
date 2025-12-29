#!/home/jugendforscht26/env/bin/python3.10

from picamera2 import Picamera2
from datetime import datetime
import time
from CNN import erkenne_muell


def main():
    try:
        picam2 = Picamera2()
        still_config = picam2.create_still_configuration()
        picam2.configure(still_config)

        print("Starte Kamera...")
        picam2.start()
        time.sleep(2)

        Uhrzeit = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"still_{Uhrzeit}.jpg"

        print(f"Nehme Foto auf: {filename}")
        picam2.capture_file(filename)
        picam2.stop()

        print("Analysiere Bild...")
        kategorie, konfidenz = erkenne_muell(filename)

        print(f"\nErkannt:  {kategorie}")
        print(f"Konfidenz: {konfidenz * 100:.2f}%")

    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer")
    except Exception as e:
        print(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            picam2.stop()
        except:
            pass


if __name__ == "__main__":
    main()