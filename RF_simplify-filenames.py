import os, re, random, string
from collections import defaultdict

COMMON_WORDS = {"image", "photo", "picture", "video", "download", "file", "document", "scan", "sample", "maxresdefault", "_n" }

# 🔹 Detectar si una palabra es hexadecimal (mínimo 5 caracteres)
def es_hexadecimal(palabra):
    return re.fullmatch(r"[a-f0-9]{5,}", palabra) is not None

# 🔹 Generar sufijo aleatorio de 2 caracteres hex
def sufijo_hex(value):
    return ''.join(random.choice('abcdef0123456789') for _ in range(value))

# 🔹 Procesar nombre de archivo
def procesar_nombre(base_name):
    filter_name = base_name
    for word in COMMON_WORDS:
        if word in base_name.lower():
            filter_name = re.sub(word, "", filter_name, flags=re.IGNORECASE)
    filter_name = filter_name.replace(".", "-").replace(",", "-")
    partes = re.split(r"([_\-])", filter_name)
    # Caso 1: nombre completo es hexadecimales
    if es_hexadecimal(base_name):
        if len(base_name) > 4:
            return base_name[:4]  # recortar a 4
    # Caso 2: nombre con texto + hexadecimales
    nuevas_partes = []
    for p in partes:
        if es_hexadecimal(p):
            continue  # eliminar hexadecimales largos
        nuevas_partes.append(p)
    # Reconstruir nombre
    nuevo_nombre = "".join(nuevas_partes)
    nuevo_nombre = nuevo_nombre.strip("-_")
    nuevo_nombre = re.sub(r"[ \-_]+", lambda m: m.group(0)[0], nuevo_nombre)
    nuevo_nombre = re.sub(r"-_|_-", "", nuevo_nombre)
    if not nuevo_nombre or nuevo_nombre in ["-", "_"]:
        return sufijo_hex(4)
    return nuevo_nombre if nuevo_nombre else sufijo_hex(4)

# 🔹 Escanear carpeta y renombrar
def renombrar_archivos(folder_path):
    existentes = set()
    print("\nSimplifying filenames:")
    for filename in os.listdir(folder_path):
        ruta_completa = os.path.join(folder_path, filename)
        if not os.path.isfile(ruta_completa):
            continue
        base_name, ext = os.path.splitext(filename)
        nuevo_base = procesar_nombre(base_name)
        nuevo_nombre = nuevo_base + ext
        # 🔸 Si el nombre ya está limpio, no renombrar
        if nuevo_nombre == filename:
            existentes.add(nuevo_nombre)
            continue
        # Evitar colisiones
        while nuevo_nombre in existentes or os.path.exists(os.path.join(folder_path, nuevo_nombre)):
            nuevo_base = nuevo_base  + sufijo_hex(2)
            nuevo_nombre = nuevo_base + ext
        # Renombrar
        os.rename(ruta_completa, os.path.join(folder_path, nuevo_nombre))
        existentes.add(nuevo_nombre)
        print(f" ▐ → {filename}\n ▐ ← {nuevo_nombre}\n ▐")

if __name__ == "__main__":
    folder = input("Enter the path of the folder to scan:\n> > > ").strip()

    if not os.path.isdir(folder):
        print("The folder does not exist or is not a valid directory.")
    else:
        renombrar_archivos(folder)
    
    input("\nPress Enter to exit.")

