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
            # 🔹 Normalizar
            base_name = base_name.lower() # Convertir a minúsculas
            base_name = base_name.replace(" ", "-").replace("_", "-").replace(".", "-") # Reemplazar espacios y guiones bajos por guiones
            base_name = re.sub(r"-\(\d+\)", "", base_name) # Eliminar patrones como "-(1)", "-(2)", etc.
            base_name = re.sub(r"-{2,}", "-", base_name) # Reemplazar múltiples guiones por uno solo
            base_name = re.sub(r"-\d+$", "", base_name) # Eliminar números al final precedidos por un guion
            base_name = base_name.strip("-")
            if es_fecha_formato(base_name):
                continue

            word_map[base_name].append(filename)
            # 🔹 Guardar subcomponentes útiles
            subwords = base_name.split("-")
            for word in subwords:
                if len(word) > 1 and not es_numero(word) and not es_hexadecimal(word):
                    word_map[word].append(filename)

    coincidences = {word: files for word, files in word_map.items() if len(files) > 1 }
    coincidences = dict(sorted(coincidences.items())) # Ordenar alfabéticamente
    return coincidences

def mostrar_coincidencias(coincidencias):
    if coincidencias:
        clear_screen()
        print("[Actualizado] Coincidencias encontradas:")
        for word in coincidencias:
            print(f" ▐ {word}")
    else:
        print(" (No quedan coincidencias)")

def guardar_coincidencias(coincidencias):
    while True:
        mostrar_coincidencias(coincidencias)
        ruta_carpeta = input("\nIntroduce la ruta de la carpeta donde guardar el archivo (ejemplo: C:/Users/Usuario/Desktop):\n> > > ").strip()

        # Validar que la ruta es una carpeta válida
        if not os.path.isdir(ruta_carpeta):
            print("\n❌ La ruta no es una carpeta válida.")
            continue

        # Construir ruta completa del archivo
        ruta_archivo = os.path.join(ruta_carpeta, "$coincidences.txt")

        # 🔹 Verificar si ya existe
        if os.path.exists(ruta_archivo):
            respuesta = input(f"\n▲ ATTENTION: El archivo \"$coincidences.txt\" ya existe. ¿Deseas sobrescribirlo? (s/n):\n> > > ").strip().lower()
            if respuesta != "s":
                continue  # vuelve a pedir ruta
        # Guardar archivo
        try:
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write("Coincidencias finales:\n")
                for word in coincidencias:
                    f.write(f"{word}\n")
            print(f"\n▲ Archivo guardado correctamente en: {ruta_archivo}")
            break  # salir del bucle al guardar con éxito
        except Exception as e:
            print(f"\nError al guardar el archivo: {e}")
            continue



def eliminar_palabras(coincidencias):
    eliminar = input("\nIntroduce las palabras que deseas eliminar (separadas por comas):\n> > > ").lower()
    palabras_a_eliminar = [p.strip() for p in eliminar.split(",")]

    for palabra in palabras_a_eliminar:
        if palabra in coincidencias:
            del coincidencias[palabra]
    clear_screen()

    return coincidencias

if __name__ == "__main__":
    folder = input("Introduce la ruta de la carpeta a escanear:\n> > > ").strip()

    if not os.path.isdir(folder):
        print("La ruta no existe o no es una carpeta válida.")
    else:

        ruta = folder
        coincidencias_global = scan_files_and_find_coincidences(folder)

        # 🔹 Bucle de eliminación hasta que el usuario esté conforme
        while True:
            mostrar_coincidencias(coincidencias_global)
            respuesta = input("\n¿Deseas eliminar alguna palabra de la lista? (s/n):\n> > > ").strip().lower()
            if respuesta == "s":
                coincidencias_global = eliminar_palabras(coincidencias_global)
            else:
                break

        # 🔹 Preguntar si desea guardar en archivo
        clear_screen()
        mostrar_coincidencias(coincidencias_global)
        guardar = input("\n¿Quieres guardar las coincidencias en un archivo .txt? (s/n):\n> > > ").strip().lower()
        if guardar == "s":
            guardar_coincidencias(coincidencias_global)

# 🔹 Mantener la ventana abierta
input("\nPresiona Enter para salir...")
