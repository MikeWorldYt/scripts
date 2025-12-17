import os, re, random, json, string
from collections import defaultdict

COMMON_WORDS = {"image", "photo", "picture", "video", "audio", "download", "file", "document", "scan", "sample", "maxresdefault", "_n", "2k", "4k", "8k", "fullhd", "1080p", "720p", "480p", "360p", "removebg", "ezgif", "ssstik",}

# 🔹 Detectar si una palabra es hexadecimal (mínimo 5 caracteres)
def es_hexadecimal(palabra):
    return re.fullmatch(r"[a-f0-9]{5,}", palabra) is not None

# 🔹 Generar sufijo aleatorio de 2 caracteres hex
def sufijo_hex(value):
    return ''.join(random.choice('abcdef0123456789') for _ in range(value))

def push_keyword(word, vars_, th):  # single append point
    if word:
        KEYWORDS.append({"word": word, "vars": vars_, "th": th})

def clear_screen():  # Funcion para limpiar la pantalla
    os.system('cls' if os.name == 'nt' else 'clear')

KEYWORDS = []

def get_keywords(ant_config):
    global KEYWORDS
    KEYWORDS.clear()

    lib_cfg = ant_config.get("LibKeywords", {})
    master_path = lib_cfg.get("master")
    filter_scope = lib_cfg.get("filter")

    if not master_path or not os.path.isfile(master_path):  # invalid source
        return

    with open(master_path, "r", encoding="utf-8") as f:
        raw_lib = json.load(f)

    if filter_scope != "global":  # navigate scoped path
        for key in filter_scope.split("."):
            raw_lib = raw_lib.get(key, {})
        if not raw_lib:
            return

    def procesar_subcategoria(subcat_name, subcat_nodo, strict=False):
    #   TOPIC LEVEL
        for entry in subcat_nodo.get("subcat", []):  
            if not strict and not entry.get("glob", False):
                continue
            push_keyword(entry.get("word"), entry.get("vars", []), None)

    #   SUBTOPIC LEVEL
        for entry in subcat_nodo.get("key", []):  
            if not strict and not entry.get("glob", False):
                continue
            push_keyword(entry.get("word"), entry.get("vars", []), subcat_name)

    # GLOBAL MODE
    if filter_scope == "global":
        for _, contenido in raw_lib.items():
            for _, subcat_nodo in contenido.items():
                if not subcat_nodo.get("cat", [{}])[0].get("glob", False):  # category gate
                    continue
                for subnombre, subnodo in subcat_nodo.items():
                    if subnombre != "cat" and isinstance(subnodo, dict):
                        procesar_subcategoria(subnombre, subnodo, strict=True)

    # SCOPED MODE
    else:
        for subnombre, subnodo in raw_lib.items():
            if isinstance(subnodo, dict):
                procesar_subcategoria(subnombre, subnodo, strict=False)

def taggear_nombre(partes):
    global KEYWORDS
    partes_filtradas = []
    topic_word = None
    subtopic_words = set()

    for p in partes:
        match = False
        p_lower = p.lower() # normalize once
        for entry in KEYWORDS:
            for v in entry["vars"]:
                if p_lower == v.lower(): # case-insensitive
                    match = True
                    if entry["th"] is None: # if no 
                        topic_word = entry["word"] # use father
                    else:
                        subtopic_words.add(entry["word"])
                        if topic_word is None: # if not topic_word
                            topic_word = entry["th"] # use father as fallback 
                    break
            if match:
                break
        if not match:
            partes_filtradas.append(p)

    # Build tag
    etiqueta = ""
    if topic_word:
        etiqueta += topic_word
    if subtopic_words:
        etiqueta += " [" + ", ".join(sorted(subtopic_words)) + "]"
    if etiqueta:
        etiqueta += "_"

    return etiqueta, partes_filtradas

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
    etiqueta, partes = taggear_nombre(partes)
    for p in partes:
        if es_hexadecimal(p):
            continue  # eliminar hexadecimales largos
        nuevas_partes.append(p)
    # Reconstruir nombre
    nuevo_nombre = etiqueta + "".join(nuevas_partes)
    nuevo_nombre = nuevo_nombre.strip("-_")
    nuevo_nombre = re.sub(r"[ \-_]+", lambda m: m.group(0)[0], nuevo_nombre)
    nuevo_nombre = re.sub(r"-_|_-", "", nuevo_nombre)
    if not nuevo_nombre or nuevo_nombre in ["-", "_"]:
        return sufijo_hex(4)
    return nuevo_nombre if nuevo_nombre else sufijo_hex(4)

# 🔹 Escanear carpeta y renombrar
def renombrar_archivos(folder_path, ant_config):
    existentes = set()
    renamed_count = 0
    untouched_count = 0
    if ant_config:
        lib_cfg = ant_config.get("LibKeywords", {})
        master_path = lib_cfg.get("master")
        if master_path and os.path.isfile(master_path):
            print("\n ▲ [INFO] Master Library online")
    print("\n Simplifying filenames:")
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
            untouched_count += 1
            continue
        # Evitar colisiones
        while nuevo_nombre in existentes or os.path.exists(os.path.join(folder_path, nuevo_nombre)):
            nuevo_base = nuevo_base  + sufijo_hex(2)
            nuevo_nombre = nuevo_base + ext
        # Renombrar
        os.rename(ruta_completa, os.path.join(folder_path, nuevo_nombre))
        existentes.add(nuevo_nombre)
        renamed_count += 1
        print(f" ▐ → {filename[:77] + '...' if len(filename) > 80 else filename}")
        print(f" ▐ ← {nuevo_nombre[:77] + '...' if len(nuevo_nombre) > 80 else nuevo_nombre}")
        print(" ▐")
    print(f" ▐\n ▐  All cleaned!\n ▐  {len(existentes)} files have been processed.")
    print(f" ▐  {renamed_count} files renamed, {untouched_count} files unchanged.")
    print(" ---------------------------------------------------------------------------")
    print(" REPORT A BUG: https://github.com/MikeWorldYt/scripts/issues/new")

if __name__ == "__main__":
    os.system("mode con: cols=100")  # Ajustar tamaño de consola en Windows
    while True:
        print("**************************************************************************")
        print("*                                                                        *")
        print("*                Filename Simplifier Script - v1.0                       *")
        print("*           by MikeWorldYt (https://github.com/MikeWorldYt)              *")
        print("*                                                                        *")
        print("*    This tool removes unnecessary identifiers and common download       *")
        print("*    words from file names, making it easier to organize your files.     *")
        print("*                                                                        *")
        print("**************************************************************************")
        print("\nGet more info: https://github.com/MikeWorldYt/scripts/wiki/Filename-Simplifier-Docs  ")
        print("\n---------------------------------------------------------------------------")
        folder = input("\nEnter the path of the folder to scan:\n> > > ").strip()
        if not os.path.isdir(folder):
            print(" ▲ [ERROR] The folder does not exist or is not a valid directory.")
        else:
            config_path = os.path.join(folder, "ant_config.json")
            ant_config = None
            if os.path.isfile(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    ant_config = json.load(f)
                extra_words = ant_config.get("simplefier", {}).get("COMMON_WORDS", [])
                librery_path = ant_config.get("LibKeywords", {}).get("master", None)
                if extra_words:
                    COMMON_WORDS.update(extra_words)
                if librery_path:
                    get_keywords(ant_config)
            renombrar_archivos(folder, ant_config)
        again = input("\nDo you want to scan another folder? (y/n):\n> > > ").strip().lower()
        clear_screen()
        if again not in ["y", ""]:
            input("\nExiting script. Goodbye!")
            break
