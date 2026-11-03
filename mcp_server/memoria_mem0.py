"""Motor de memoria con mem0 (Proyecto 5), 100 % local: Ollama + pgvector.

Lo usa server.py cuando en el .env pone MEMORIA_MOTOR=mem0. Las tools son las mismas
(recordar, consultar_memoria, olvidar); solo cambia quién guarda por dentro:

    propia -> la tabla `memoria`: se guarda la frase EXACTA que confirma la persona.
    mem0   -> el modelo lee la frase y decide qué "hechos" guardar (infer=True).

Lo aprendido en mcp_server/probar_mem0.py está aplicado aquí:
  - telemetría apagada ANTES de importar mem0,
  - sin historial SQLite (SinHistorial): olvidar es olvidar,
  - thinking apagado (si no, el modelo se queda sin tokens y mem0 guarda 0 sin avisar),
  - instrucciones para que escriba en español y sin traducir términos de barbería.
OJO: aquí no se usa print(): el servidor MCP habla por stdout y un print lo rompería.
"""
import os
import re
from pathlib import Path

os.environ["MEM0_TELEMETRY"] = "False"
CARPETA = Path(__file__).resolve().parent.parent / "mem0_datos"
CARPETA.mkdir(exist_ok=True)
os.environ["MEM0_DIR"] = str(CARPETA)

from mem0 import Memory  # noqa: E402

OLLAMA = "http://localhost:11434"
# Un id de mem0 es un UUID, p. ej. "3f2b9c1e-8a4d-4e6f-9b1a-2c3d4e5f6a7b".
PATRON_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class SinHistorial:
    """Sustituye al historial SQLite de mem0 y NO guarda nada (ver probar_mem0.py)."""

    def _descartar(self, *args, **kwargs):
        pass

    save_messages = add_history = batch_add_history = _descartar

    def get_last_messages(self, *args, **kwargs):
        return []

    def get_history(self, *args, **kwargs):
        return []

    def reset(self):
        pass

    def close(self):
        pass


def crear_memoria() -> Memory:
    config = {
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
            "collection_name": "mem0_memoria",  # la de verdad (la prueba usa mem0_prueba)
            "embedding_model_dims": 1024}},
        "history_db_path": ":memory:",
        "custom_instructions": (
            "Escribe cada recuerdo en español, con las mismas palabras del usuario. "
            "No traduzcas términos de barbería (degradado, fade, máquina del 0). "
            "Un hecho por recuerdo."
        ),
    }
    m = Memory.from_config(config)
    m.db.close()
    m.db = SinHistorial()

    chat_original = m.llm.client.chat

    def chat_sin_pensar(**kwargs):
        kwargs["think"] = False
        return chat_original(**kwargs)

    m.llm.client.chat = chat_sin_pensar
    return m


_memoria = None


def memoria() -> Memory:
    """Crea mem0 la primera vez que se usa (así el servidor arranca rápido)."""
    global _memoria
    if _memoria is None:
        _memoria = crear_memoria()
    return _memoria


def user_id(barberia_id: int, cliente_id: int) -> str:
    """El "dueño" de cada recuerdo en mem0. Ejemplo: Pedro de El Navajas -> "b1-c1".
    El aislamiento depende de este texto (un FILTRO), no de una FK como en la tabla memoria."""
    return f"b{barberia_id}-c{cliente_id}"


def listar(barberia_id: int, cliente_id: int) -> list[dict]:
    """Todos los recuerdos de un cliente, en el mismo formato que la memoria propia."""
    r = memoria().get_all(filters={"user_id": user_id(barberia_id, cliente_id)}, top_k=100)
    datos = [{"id": x["id"], "dato": x["memory"], "fecha": (x.get("created_at") or "")[:10]}
             for x in r.get("results", [])]
    return sorted(datos, key=lambda d: d["fecha"])


def recordar(barberia_id: int, cliente_id: int, dato: str, dato_prohibido) -> dict:
    """Le pasa la frase a mem0 y revisa lo que el modelo ha decidido guardar.

    El filtro se aplica DOS veces: server.py antes de llamar aquí (la frase que escribe la
    persona) y aquí después, porque el modelo REDACTA el recuerdo y podría escribir algo
    que la frase original no decía tal cual. Si un recuerdo nuevo no pasa, se borra al momento.
    """
    m = memoria()
    r = m.add(dato, user_id=user_id(barberia_id, cliente_id))
    guardados, rechazados = [], []
    for x in r.get("results", []):
        motivo = dato_prohibido(x.get("memory", ""))
        if motivo:
            m.delete(x["id"])
            rechazados.append({"dato": x.get("memory"), "motivo": motivo})
        else:
            guardados.append({"id": x["id"], "dato": x.get("memory"), "evento": x.get("event")})
    return {"guardados": guardados, "rechazados": rechazados}


def olvidar(barberia_id: int, dato_id: str) -> dict | None:
    """Borra un recuerdo SOLO si es de un cliente de esta barbería. Si no, None
    (server.py responde "No existe el dato ..." igual que la memoria propia)."""
    if not PATRON_UUID.fullmatch(str(dato_id)):
        return None
    m = memoria()
    x = m.get(str(dato_id))
    if x is None or not str(x.get("user_id", "")).startswith(f"b{barberia_id}-c"):
        return None
    # mem0 solo limpia su tabla de "entidades" (nombres sacados de los recuerdos) si ya la
    # ha abierto en este proceso. Tocarla aquí evita que queden nombres huérfanos al olvidar
    # justo después de reiniciar el servidor.
    m.entity_store  # noqa: B018
    m.delete(str(dato_id))
    return {"id": x["id"], "dato": x["memory"]}
