import os
import re
from collections import defaultdict

# 🔹 Variable global para almacenar coincidencias
coincidencias_global = {}

def clear_screen():  # Funcion para limpiar la pantalla
    os.system('cls' if os.name == 'nt' else 'clear')

def scan_files_and_find_coincidences(folder_path):
    word_map = defaultdict(list)

    for filename in os.listdir(folder_path):
        if os.path.isfile(os.path.join(folder_path, filename)):
            # 🔹 Separar nombre base y extensión
            base_name, _ = os.path.splitext(filename)
            words = re.findall(r"[a-zA-Z0-9]+", base_name.lower())
            for word in words:
                word_map[word].append(filename)

    coincidences = {word: files for word, files in word_map.items() if len(files) > 1}
    return coincidences

def mostrar_coincidencias(coincidencias):
    if coincidencias:
        for word in coincidencias:
            print(f" ▐ {word}")
    else:
        print(" (No quedan coincidencias)")

def eliminar_palabras(coincidencias):
    eliminar = input("\nIntroduce las palabras que deseas eliminar (separadas por comas): ").lower()
    palabras_a_eliminar = [p.strip() for p in eliminar.split(",")]

    for palabra in palabras_a_eliminar:
        if palabra in coincidencias:
            del coincidencias[palabra]
    clear_screen()

    return coincidencias

if __name__ == "__main__":
    folder = input("Introduce la ruta de la carpeta a escanear: ").strip()

    if not os.path.isdir(folder):
        print("La ruta no existe o no es una carpeta válida.")
    else:
        clear_screen()
        coincidencias_global = scan_files_and_find_coincidences(folder)

        # 🔹 Bucle de eliminación hasta que el usuario esté conforme
        while True:
            print("[Actualizado] Coincidencias encontradas:")
            mostrar_coincidencias(coincidencias_global)
            respuesta = input("\n¿Deseas eliminar alguna palabra de la lista? (s/n): ").strip().lower()
            if respuesta == "s":
                coincidencias_global = eliminar_palabras(coincidencias_global)
            else:
                break

# 🔹 Mantener la ventana abierta
input("\nPresiona Enter para salir...")
