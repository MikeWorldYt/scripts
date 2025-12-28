import os, re, random, json, string
from collections import defaultdict

COMMON_WORDS = {"image", "photo", "picture", "video", "audio", "download", "file", "document", "scan", "sample", "maxresdefault", "_n", "2k", "4k", "8k", "fullhd", "1080p", "720p", "480p", "360p", "removebg", "ezgif", "ssstik",}

# 🔹 Detectar si una palabra es hexadecimal (mínimo 5 caracteres)
def es_hexadecimal(palabra):
    return re.fullmatch(r"[a-f0-9]{5,}", palabra) is not None

# 🧪 EXPERIMENTAL
def remove_hexadecimal(palabra):
    tokens = re.findall(r"\([^)]*\)|\[[^\]]*\]|[^()\[\]]+", palabra)
    nuevos = []
    for t in tokens:
        if t.startswith("(") or t.startswith("["):
            # mantener íntegros los bloques con paréntesis/corchetes
            nuevos.append(t)
        else:
            if not es_hexadecimal(t):
                continue 
            # limpiar decoraciones y evaluar como hex
            plain = re.sub(r"[^a-f0-9]", "", t.lower())
            if re.fullmatch(r"[a-f0-9]{5,}", plain):
                nuevos.append(plain[:4])  # truncar a 4
            else:
                nuevos.append(t)

    return " ".join(nuevos)

# 🔹 Generar sufijo aleatorio de 2 caracteres hex
def sufijo_hex(value):
    return ''.join(random.choice('abcdef0123456789') for _ in range(value))

def push_keyword(word, vars_, th):  # single append point
    base_terms = vars_ or []
    variantes = set()
    for t in base_terms:
        t = t.strip()
        variantes.add(t)
        variantes.add(t.replace(" ", "_"))
        variantes.add(t.replace(" ", "-"))
    KEYWORDS.append({"word": word, "vars": list(variantes), "th": th})

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

def detectar_etiqueta_previa(filter_name):
    match = re.match(r"^([^\[\]_]+)\s*\[([^\[\]]+)\]_", filter_name)
    if match:
        etiqueta_previa = f"{match.group(1)} [{match.group(2)}]_"
        filter_name = filter_name[match.end():]
        return etiqueta_previa, filter_name
    return "", filter_name

def taggear_nombre(filter_name):
    global KEYWORDS
    topic_word = None
    subtopic_words = set()

    for entry in KEYWORDS:
        for v in entry["vars"]:
            pat = r"(?<![A-Za-z0-9])" + re.escape(v) + r"(?![A-Za-z0-9])"
            if re.search(pat, filter_name, flags=re.IGNORECASE): # search coincidences
                filter_name = re.sub(pat, "", filter_name, flags=re.IGNORECASE) # remove coincidences
                # Etiquetado
                if entry["th"] is None: # if no topic
                    topic_word = entry["word"] # use father
                else:
                    subtopic_words.add(entry["word"])
                    if topic_word is None: # if not topic_word
                        topic_word = entry["th"] # use father as fallback 
                break
    def norm_tag(texto):
        return re.sub(r"[ _]+", "-", texto.strip())
    # Build tag
    etiqueta = ""
    if topic_word:
        etiqueta = norm_tag(topic_word)
        etiqueta += " [" + ", ".join(sorted(norm_tag(s) for s in subtopic_words)) + "]" if subtopic_words else " [$uk]"
        etiqueta += "_"
    return etiqueta, filter_name

# 🔹 Procesar nombre de archivo
def procesar_nombre(base_name):
    # base_name = remove_hexadecimal(base_name) # TESTING
    filter_name = base_name
    if es_hexadecimal(base_name) and len(base_name) > 4: # cut first 4 chars if its only hex
        return base_name[:4]
    for word in COMMON_WORDS: # remove common words
        if word in base_name.lower():
            filter_name = re.sub(word, "", filter_name, flags=re.IGNORECASE)
    filter_name = filter_name.replace(".", "-").replace(",", "-") # normalize separators
##  METADATA TAG PROCESSING :
    etiqueta_previa, filter_name = detectar_etiqueta_previa(filter_name)
    etiqueta_nueva, filter_name = taggear_nombre(filter_name)
    def es_etiqueta_valida(etiqueta): # validate if a new tag is not a generic tag
        return bool(re.search(r"\[[^\[\]]+\]", etiqueta)) and "$uk" not in etiqueta
    etiqueta = etiqueta_nueva if es_etiqueta_valida(etiqueta_nueva) else etiqueta_previa
## NAME PARTS PROCESSING :
    partes = re.split(r"([_\-])", filter_name)
    nuevas_partes = [p for p in partes if not es_hexadecimal(p)] # remove hexadecimals
## REBUILDING AND CLEANING :
    nuevo_nombre = etiqueta + "".join(nuevas_partes) # rebuild
    nuevo_nombre = nuevo_nombre.strip("-_ ") # clean residuals at start/end
    nuevo_nombre = re.sub(r"[ \-_]+", lambda m: m.group(0)[0], nuevo_nombre) # remove multiple separators
    nuevo_nombre = re.sub(r"-_|_-", "", nuevo_nombre) # remove hybrid separators
    return nuevo_nombre if nuevo_nombre not in ("", "-", "_") else sufijo_hex(4)

# 🔹 Escanear carpeta y renombrar
def renombrar_archivos(folder_path, ant_config):
    existentes = set()
    renamed_count = 0
    untouched_count = 0
    ignore_list = set()
    ignore_exts = set()
    ignore_prefixes = set("~#@!")
    if ant_config:
        lib_cfg = ant_config.get("LibKeywords", {})
        master_path = lib_cfg.get("master")
        if master_path and os.path.isfile(master_path):
            print("\n ▲ [INFO] Master Library online")
        ignore_list = set(ant_config.get("simplefier", {}).get("ignore_files", []))
        ignore_exts = set(ant_config.get("simplefier", {}).get("ignore_ext", []))
    print("\n Simplifying filenames:")
    for filename in os.listdir(folder_path):
        if filename in ignore_list or filename[:1] in ignore_prefixes or any(filename.endswith(ext) for ext in ignore_exts): # Ignore system files and special files
            untouched_count += 1
            continue
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
