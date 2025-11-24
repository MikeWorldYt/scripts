import os
import re
from collections import defaultdict

# 🔹 Variable global para almacenar coincidencias
coincidencias_global = {}
ruta = ""

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

def guardar_coincidencias(coincidencias):
    ruta_carpeta = input("\nIntroduce la ruta de la carpeta donde guardar el archivo (ejemplo: C:/Users/Usuario/Desktop):\n ").strip()

    # Validar que la ruta es una carpeta válida
    if not os.path.isdir(ruta_carpeta):
        print("\n❌ La ruta no es una carpeta válida.")
        return

    # Construir ruta completa del archivo
    ruta_archivo = os.path.join(ruta_carpeta, "$coincidences.txt")

    try:
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(f"Coincidencias de {ruta}:\n")
            for word in coincidencias:
                f.write(f"{word}\n")
        print(f"\n✅ Archivo guardado correctamente en: {ruta_archivo}")
    except Exception as e:
        print(f"\n❌ Error al guardar el archivo: {e}")


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
        ruta = folder
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

        # 🔹 Preguntar si desea guardar en archivo
        guardar = input("\n¿Quieres guardar las coincidencias en un archivo .txt? (s/n): ").strip().lower()
        if guardar == "s":
            guardar_coincidencias(coincidencias_global)

# 🔹 Mantener la ventana abierta
input("\nPresiona Enter para salir...")
