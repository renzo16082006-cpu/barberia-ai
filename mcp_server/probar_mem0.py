"""Prueba aislada de mem0 (Proyecto 5): 100 % local con Ollama + pgvector.

Ejecutar:  uv run python mcp_server\\probar_mem0.py 2>$null
Necesita Docker (barberia-db) y Ollama en marcha.

Qué comprueba:
  1. add()    -> el modelo extrae "hechos" de una frase y los guarda.
  2. search() -> los encuentra por similitud, solo para ESE cliente.
  3. Aislamiento: el Pedro de Corte Fino (b2-c4) no ve nada.
  4. delete_all() -> borra... ¿todo? (miramos qué queda en el historial).
"""
import os
import sqlite3
import time
from pathlib import Path

# --- Seguridad: ANTES de importar mem0 -------------------------------------
# mem0 lee MEM0_TELEMETRY una sola vez, al importarse, y por defecto es "True".
# Lo fijamos en el código (no en el .env) para que falle cerrado.
os.environ["MEM0_TELEMETRY"] = "False"
# Sus archivos (historial SQLite, config) dentro del proyecto, en una carpeta
# ignorada por Git, en vez de C:\\Users\\renzo\\.mem0
CARPETA = Path(__file__).resolve().parent.parent / "mem0_datos"
CARPETA.mkdir(exist_ok=True)
os.environ["MEM0_DIR"] = str(CARPETA)

from dotenv import load_dotenv  # noqa: E402
from mem0 import Memory  # noqa: E402

load_dotenv()

OLLAMA = "http://localhost:11434"
HISTORIAL = CARPETA / "historial.db"

CONFIG = {
    # Nombres EXACTOS de modelos que ya tienes: si no existen, mem0 los descarga solo.
    "llm": {"provider": "ollama", "config": {
        "model": "qwen3.5:4b", "temperature": 0, "max_tokens": 2000,
        "ollama_base_url": OLLAMA}},
    "embedder": {"provider": "ollama", "config": {
        "model": "bge-m3", "embedding_dims": 1024, "ollama_base_url": OLLAMA}},
    "vector_store": {"provider": "pgvector", "config": {
        "host": "127.0.0.1", "port": 5432,
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "dbname": os.environ["POSTGRES_DB"],
        "collection_name": "mem0_prueba",   # tabla propia, separada de `memoria`
        "embedding_model_dims": 1024}},
    "history_db_path": str(HISTORIAL),
    # mem0 2.2.1 traduce al inglés por defecto (use_input_language=False y no
    # se puede cambiar desde la config). Se lo pedimos con instrucciones propias.
    "custom_instructions": (
        "Escribe cada recuerdo en español, con las mismas palabras del usuario. "
        "No traduzcas términos de barbería (degradado, fade, máquina del 0). "
        "Un hecho por recuerdo."
    ),
}

PEDRO_NAVAJAS = "b1-c1"   # barberia 1, cliente 1
PEDRO_CORTE_FINO = "b2-c4"  # mismo nombre, otra barbería


def cronometro(texto, funcion):
    inicio = time.perf_counter()
    resultado = funcion()
    print(f"   ({texto}: {time.perf_counter() - inicio:.1f} s)")
    return resultado


print("0) Creando Memory (conecta con Postgres y Ollama)...")
m = cronometro("arranque", lambda: Memory.from_config(CONFIG))

# mem0 no deja configurar el "thinking" de Ollama y qwen3.5 piensa por defecto.
# Envolvemos la llamada para (a) apagarlo, como en el harness, y (b) ver qué
# devuelve el modelo: si falla, mem0 lo convierte en "0 recuerdos" sin avisar.
PENSAR = False
_chat_original = m.llm.client.chat


def chat_vigilado(**kwargs):
    kwargs["think"] = PENSAR
    respuesta = _chat_original(**kwargs)
    pensado = respuesta.message.thinking or ""
    texto = respuesta.message.content or ""
    print(f"   [modelo] fin={respuesta.done_reason} pensado={len(pensado)} car. "
          f"respuesta={len(texto)} car.")
    print(f"   [modelo] {texto[:300]!r}")
    return respuesta


m.llm.client.chat = chat_vigilado

print("\n1) add() con infer=True: el modelo decide qué guardar")
frase = "Pedro prefiere el degradado bajo y que le atienda Carlos."
print(f"   Frase: {frase}")
r = cronometro("add", lambda: m.add(frase, user_id=PEDRO_NAVAJAS))
for item in r.get("results", []):
    print(f"   [{item.get('event')}] {item.get('memory')}")

print("\n2) search() para Pedro de El Navajas")
r = cronometro("search", lambda: m.search("¿qué corte le gusta?", filters={"user_id": PEDRO_NAVAJAS}))
for item in r.get("results", []):
    print(f"   {item.get('score', 0):.2f}  {item.get('memory')}")

print("\n3) Aislamiento: misma búsqueda para Pedro de Corte Fino")
r = m.search("¿qué corte le gusta?", filters={"user_id": PEDRO_CORTE_FINO})
print(f"   Resultados: {len(r.get('results', []))} (esperado: 0; solo vale si en el 2) hubo resultados)")

print("\n4) delete_all() de Pedro de El Navajas")
m.delete_all(user_id=PEDRO_NAVAJAS)
r = m.get_all(filters={"user_id": PEDRO_NAVAJAS})
print(f"   Recuerdos que quedan en pgvector: {len(r.get('results', []))} (esperado: 0)")

print("\n5) ¿Y en el historial SQLite de mem0?")
con = sqlite3.connect(HISTORIAL)
for tabla in ("history", "messages"):
    n = con.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]
    print(f"   Filas en {tabla}: {n}")
con.close()
