import os
import re
from collections import defaultdict

def scan_files_and_find_coincidences(folder_path):
    word_map = defaultdict(list)

    for filename in os.listdir(folder_path):
        if os.path.isfile(os.path.join(folder_path, filename)):
            words = re.findall(r"[a-zA-Z0-9]+", filename.lower())
            for word in words:
                word_map[word].append(filename)

    coincidences = {word: files for word, files in word_map.items() if len(files) > 1}
    return coincidences


if __name__ == "__main__":
    # 🔹 Aquí pedimos al usuario la ruta
    folder = input("Introduce la ruta de la carpeta a escanear: ").strip()

    if not os.path.isdir(folder):
        print("La ruta no existe o no es una carpeta válida.")
    else:
        result = scan_files_and_find_coincidences(folder)

        print("\nCoincidencias encontradas:")
        for word, files in result.items():
            print(f" ▐ {word}")


# 🔹 Mantener la ventana abierta
input("\nPresiona Enter para salir...")
