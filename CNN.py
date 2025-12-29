#!/home/jugendforscht26/env/bin/python3.10
import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite
import os

_interpreter = None
_input_details = None
_output_details = None

Class_Names = [
    'cardboard',
    'glass',
    'metal',
    'paper',
    'plastic',
    'trash'
]


def _lade_modell():
    global _interpreter, _input_details, _output_details

    if _interpreter is None:
        if not os.path.exists('model.tflite'):
            raise FileNotFoundError("model.tflite nicht gefunden!")

        _interpreter = tflite.Interpreter(model_path='model.tflite')
        _interpreter.allocate_tensors()
        _input_details = _interpreter.get_input_details()
        _output_details = _interpreter.get_output_details()
        print("Modell geladen")


def erkenne_muell(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Bild nicht gefunden: {filename}")

    _lade_modell()

    img = Image.open(filename)
    img = img.resize((299, 299))
    img = img.convert('RGB')

    bild_array = np.array(img, dtype=np.float32)
    bild_array = bild_array / 255.0
    bild_array = np.expand_dims(bild_array, axis=0)

    _interpreter.set_tensor(_input_details[0]['index'], bild_array)
    _interpreter.invoke()
    prediction = _interpreter.get_tensor(_output_details[0]['index'])

    klasse = np.argmax(prediction[0])
    konfidenz = prediction[0][klasse]

    return Class_Names[klasse], konfidenz


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        kategorie, konfidenz = erkenne_muell(sys.argv[1])
        print(f"Kategorie: {kategorie}")
        print(f"Konfidenz: {konfidenz * 100:.2f}%")
    else:
        print("Verwendung: python CNN.py <bild.jpg>")