"""Harness de agente propio: el bucle modelo <-> tools, sin frameworks.

Ejemplo de una vuelta:
    Tú: "Cancela la cita 4"
    modelo  -> quiere cancelar_cita(cita_id=4)
    harness -> es de ESCRITURA: se para y pide confirmación al humano
    humano  -> sí
    harness -> ejecuta la tool en el servidor MCP y le da el resultado al modelo
    modelo  -> "Listo, la cita 4 queda cancelada."

Reglas de seguridad (las impone ESTE código, no el modelo):
1. Límite de pasos por pregunta (MAX_PASOS): si el modelo entra en bucle, se corta.
2. Las tools de escritura no se ejecutan sin confirmación humana, y se confirma
   con los argumentos REALES de la llamada, no con lo que el modelo diga en el texto.
3. Las tools son las del servidor MCP: el aislamiento por barbería sigue en el servidor.
"""
import asyncio
import json
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "mcp_server"))

from fastmcp import Client  # noqa: E402

from server import MADRID, NOMBRE_BARBERIA, mcp  # noqa: E402

OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO = "qwen3.5:4b"  # el mejor del eval (22/25) y el que menos VRAM usa
MAX_PASOS = 6  # llamadas al modelo por pregunta
ESCRITURA = {"crear_cita", "cancelar_cita"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def fechas() -> str:
    # Las fechas relativas las calcula el CÓDIGO: el modelo solo tiene que copiarlas.
    hoy = datetime.now(MADRID)
    ayer = hoy - timedelta(days=1)
    proximos = ", ".join(
        f"{DIAS[d.weekday()]} {d:%Y-%m-%d}" for d in (hoy + timedelta(days=i) for i in range(1, 8))
    )
    return (
        f"Hoy es {DIAS[hoy.weekday()]} {hoy:%Y-%m-%d} y son las {hoy:%H:%M} (Europe/Madrid). "
        f"Ayer fue {ayer:%Y-%m-%d}. Mañana es {DIAS[(hoy + timedelta(days=1)).weekday()]} "
        f"{hoy + timedelta(days=1):%Y-%m-%d}. Próximos días: {proximos}. "
    )


def prompt_interno() -> str:
    return (
        f"Eres el asistente interno de la barbería {NOMBRE_BARBERIA}; hablas con el personal. {fechas()}"
        "Usa las tools para consultar o modificar datos; nunca inventes datos. "
        "Si una tool devuelve un error, explícaselo al usuario con tus palabras. "
        "Responde en español, breve y claro."
    )


def prompt_cliente() -> str:
    return (
        f"Eres el asistente de la web pública de la barbería {NOMBRE_BARBERIA}; hablas con clientes. {fechas()}"
        "Responde SOLO sobre horarios, normas (cancelaciones, pagos), cuidados y la barbería, "
        "usando consultar_documentos; si los documentos no lo dicen, di que no lo sabes. "
        "No tienes acceso a la agenda ni a datos de clientes: para reservar, cambiar o anular "
        "una cita, indica que llamen a la barbería. Si la pregunta no trata de la barbería "
        "(matemáticas, videojuegos, noticias, deberes...), no la respondas. "
        "Responde en español, breve y amable."
    )


# Permisos por rol: el CÓDIGO decide qué tools recibe cada asistente.
# Una tool que no está en la lista no se le enseña al modelo y, si la pide igualmente, no se ejecuta.
ROLES = {
    "interno": {"tools": None, "prompt": prompt_interno, "exige_documentos": False},  # None = todas
    "cliente": {"tools": {"consultar_documentos"}, "prompt": prompt_cliente, "exige_documentos": True},
}

# Si el asistente de clientes contesta SIN haber mirado los documentos, no se fía de él:
# o es una pregunta fuera de tema o se lo está inventando. Lo decide el código, no el modelo.
FUERA_DE_TEMA = (
    "Solo puedo ayudarte con dudas de la barbería: horarios, precios, cómo cancelar o cambiar una cita, "
    "formas de pago y cuidados después del corte. Para reservar, llama o escribe por WhatsApp al "
    "977 000 111. ¿Qué quieres saber?"
)


def llamar_modelo(mensajes: list, tools: list) -> dict:
    """Una llamada a Ollama (sin streaming). Devuelve el mensaje del asistente."""
    cuerpo = {
        "model": MODELO,
        "messages": mensajes,
        "tools": tools,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_ctx": 8192},
    }
    peticion = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(peticion, timeout=300) as r:
        return json.loads(r.read())["message"]


class Agente:
    def __init__(self, client: Client, tools: list, rol: str = "interno"):
        permitidas = ROLES[rol]["tools"]
        self.client = client
        self.rol = rol
        self.todas = tools  # para poder crear otra conversación igual (reiniciar)
        self.tools = [t for t in tools if permitidas is None or t["function"]["name"] in permitidas]
        self.nombres = {t["function"]["name"] for t in self.tools}
        self.mensajes = [{"role": "system", "content": ROLES[rol]["prompt"]()}]
        self.cola = []  # llamadas a tools que el modelo pidió y aún no se han hecho
        self.pendiente = None  # llamada de escritura esperando confirmación
        self.pasos = 0
        self.traza = []  # qué tools se han usado en esta pregunta (para mostrarlo)

    @classmethod
    async def crear(cls, client: Client, rol: str = "interno") -> "Agente":
        tools = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description or "", "parameters": t.input_schema},
            }
            for t in await client.list_tools()
        ]
        return cls(client, tools, rol)

    async def preguntar(self, texto: str) -> dict:
        if self.pendiente:
            return self._respuesta("Primero responde sí o no a la acción pendiente.")
        self.mensajes.append({"role": "user", "content": texto})
        self.pasos = 0
        self.traza = []
        return await self._bucle()

    async def confirmar(self, si: bool) -> dict:
        if not self.pendiente:
            return self._respuesta("No hay ninguna acción pendiente.")
        llamada, self.pendiente = self.pendiente, None
        if not si:
            # Ante un "no", responde el CÓDIGO (siempre igual) y se descarta el resto del turno:
            # el modelo no improvisa ni vuelve a insistir.
            self.traza.append(f"✋ {llamada['function']['name']} rechazada por el usuario")
            self._guardar_resultado(llamada, {"error": "El usuario ha respondido NO. No se ha ejecutado."})
            self.cola = []
            texto = "De acuerdo, no lo hago. No se ha cambiado nada."
            self.mensajes.append({"role": "assistant", "content": texto})
            return self._respuesta(texto)
        self._guardar_resultado(llamada, await self._ejecutar(llamada))
        return await self._bucle()

    async def _bucle(self) -> dict:
        while True:
            # 1) Hacer las llamadas pendientes; si una es de escritura, parar y preguntar.
            while self.cola:
                llamada = self.cola.pop(0)
                nombre = llamada["function"]["name"]
                # Solo se pide confirmación si el rol TIENE esa tool; si no, _ejecutar la bloquea (⛔).
                if nombre in ESCRITURA and nombre in self.nombres:
                    self.pendiente = llamada
                    return {
                        "tipo": "confirmar",
                        "tool": nombre,
                        "argumentos": self._argumentos(llamada),
                        "traza": self.traza,
                    }
                self._guardar_resultado(llamada, await self._ejecutar(llamada))

            # 2) Límite de pasos: lo decide el código, no el modelo.
            if self.pasos >= MAX_PASOS:
                return self._respuesta("He parado: necesitaba demasiados pasos. Prueba a pedirlo de otra forma.")
            self.pasos += 1

            # 3) Preguntar al modelo (en otro hilo para no bloquear la web).
            msg = await asyncio.to_thread(llamar_modelo, self.mensajes, self.tools)
            self.mensajes.append(
                {"role": "assistant", "content": msg.get("content", ""), "tool_calls": msg.get("tool_calls", [])}
            )
            if not msg.get("tool_calls"):
                texto = msg.get("content", "")
                # Cuenta solo tools EJECUTADAS (🔧): un intento bloqueado (⛔) no es haber mirado los documentos.
                if ROLES[self.rol]["exige_documentos"] and not any(t.startswith("🔧") for t in self.traza):
                    texto = FUERA_DE_TEMA
                    self.mensajes[-1]["content"] = texto  # el historial guarda lo que de verdad se mostró
                return self._respuesta(texto)
            self.cola = list(msg["tool_calls"])

    @staticmethod
    def _argumentos(llamada: dict) -> dict:
        args = llamada["function"].get("arguments") or {}
        return json.loads(args) if isinstance(args, str) else args

    async def _ejecutar(self, llamada: dict) -> dict:
        nombre = llamada["function"]["name"]
        if nombre not in self.nombres:  # tool inventada o no permitida para este rol
            self.traza.append(f"⛔ {nombre} (no permitida)")
            return {"error": f"La tool {nombre} no existe o no está permitida."}
        args = self._argumentos(llamada)
        self.traza.append(f"🔧 {nombre}({', '.join(f'{k}={v}' for k, v in args.items())})")
        try:
            return (await self.client.call_tool(nombre, args)).data
        except Exception as e:  # los errores del servidor (permisos, validación) vuelven al modelo
            return {"error": str(e)}

    def _guardar_resultado(self, llamada: dict, resultado) -> None:
        self.mensajes.append(
            {
                "role": "tool",
                "tool_name": llamada["function"]["name"],
                "content": json.dumps(resultado, ensure_ascii=False, default=str),
            }
        )

    def _respuesta(self, texto: str) -> dict:
        return {"tipo": "respuesta", "texto": texto, "traza": self.traza}


def leer(pregunta: str) -> str:
    # print + input por separado: en Windows input("...") escribe la pregunta por stderr,
    # y con 2>$null no se vería.
    print(pregunta, end="", flush=True)
    return input().strip()


async def chat_terminal():
    async with Client(mcp) as client:
        agente = await Agente.crear(client)
        print(f"Asistente de {NOMBRE_BARBERIA} ({MODELO}). Escribe 'salir' para terminar.")
        while True:
            texto = leer("\nTú: ")
            if texto.lower() in {"salir", "exit"}:
                break
            if not texto:
                continue
            r = await agente.preguntar(texto)
            while r["tipo"] == "confirmar":
                for linea in r["traza"]:
                    print("   ", linea)
                print(f"\n⚠️  El asistente quiere ejecutar {r['tool']} con: {r['argumentos']}")
                si = leer("¿Lo confirmas? (s/n): ").lower() in {"s", "si", "sí"}
                r = await agente.confirmar(si)
            for linea in r["traza"]:
                print("   ", linea)
            print("Asistente:", r["texto"])


if __name__ == "__main__":
    asyncio.run(chat_terminal())
