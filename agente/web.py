"""Web de chat de la barbería, encima del harness (agente/harness.py).

Arrancar:  uv run python agente\\web.py
  http://127.0.0.1:8000/       web pública de la barbería + asistente para CLIENTES (solo documentos)
  http://127.0.0.1:8000/panel  panel INTERNO del personal (todas las tools, confirma antes de escribir)
  En producción /panel y /api/interno necesitarían login; aquí los protege que solo se escucha en 127.0.0.1.

Seguridad:
- Solo escucha en 127.0.0.1: nadie de tu red (ni del wifi) puede entrar.
- Anti-CSRF: los POST a /api deben ser JSON y traer Origin = esta misma web. Así otra
  página que visites no puede mandar "confirmar" a tu asistente por detrás.
- Content-Security-Policy: el navegador solo ejecuta scripts servidos por esta web
  (por eso el JS va en un archivo aparte y no dentro del HTML).
- La página pinta las respuestas con textContent, nunca innerHTML: si el modelo
  devuelve HTML o un <script>, se ve como texto y no se ejecuta.
- Límites de tamaño (petición y mensaje) y errores internos sin detalles para el navegador.
"""
import asyncio
import contextlib
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from harness import MODELO, NOMBRE_BARBERIA, Agente, Client, mcp

HOST, PUERTO = "127.0.0.1", 8000
ORIGENES = {f"http://{HOST}:{PUERTO}", f"http://localhost:{PUERTO}"}
MAX_TEXTO = 1000  # caracteres por mensaje
ESTATICOS = Path(__file__).resolve().parent / "static"

ROLES_WEB = {"cliente", "interno"}
agentes = {}  # una conversación por rol (demo local)
candado = asyncio.Lock()  # una petición cada vez: el agente no se mezcla


@contextlib.asynccontextmanager
async def lifespan(app):
    async with Client(mcp) as client:
        for rol in ROLES_WEB:
            agentes[rol] = await Agente.crear(client, rol)
        yield


async def seguridad(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method == "POST":
        if request.headers.get("origin") not in ORIGENES:
            return JSONResponse({"error": "Origen no permitido"}, status_code=403)
        if not request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"error": "Se esperaba JSON"}, status_code=415)
    respuesta = await call_next(request)
    respuesta.headers["Content-Security-Policy"] = (
        "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    return respuesta


def error(texto: str, codigo: int = 400) -> JSONResponse:
    return JSONResponse({"tipo": "error", "texto": texto, "traza": []}, status_code=codigo)


async def leer_json(request: Request) -> dict:
    try:
        datos = await request.json()
    except Exception:
        return {}
    return datos if isinstance(datos, dict) else {}


async def ejecutar(corrutina) -> JSONResponse:
    async with candado:
        try:
            return JSONResponse(await corrutina)
        except Exception as e:  # el detalle va a la terminal, no al navegador
            print("ERROR:", repr(e))
            return error("Ha fallado algo al hablar con el modelo. ¿Está Ollama en marcha?", 500)


async def portada(request: Request):
    return FileResponse(ESTATICOS / "barberia.html")


async def panel(request: Request):
    return FileResponse(ESTATICOS / "index.html")


def agente_de(request: Request):
    return agentes.get(request.path_params["rol"])  # None si el rol no existe


async def info(request: Request):
    return JSONResponse({"barberia": NOMBRE_BARBERIA, "modelo": MODELO})


async def chat(request: Request):
    agente = agente_de(request)
    if agente is None:
        return error("No encontrado.", 404)
    texto = (await leer_json(request)).get("texto")
    if not isinstance(texto, str) or not texto.strip():
        return error("Escribe un mensaje.")
    if len(texto) > MAX_TEXTO:
        return error(f"Mensaje demasiado largo (máximo {MAX_TEXTO} caracteres).")
    return await ejecutar(agente.preguntar(texto.strip()))


async def confirmar(request: Request):
    agente = agente_de(request)
    if agente is None:
        return error("No encontrado.", 404)
    si = (await leer_json(request)).get("si")
    if not isinstance(si, bool):
        return error("Falta la respuesta sí/no.")
    return await ejecutar(agente.confirmar(si))


async def reiniciar(request: Request):
    viejo = agente_de(request)
    if viejo is None:
        return error("No encontrado.", 404)
    async with candado:
        agentes[viejo.rol] = Agente(viejo.client, viejo.todas, viejo.rol)
    return JSONResponse({"ok": True})


app = Starlette(
    routes=[
        Route("/", portada),
        Route("/panel", panel),
        Route("/api/info", info),
        Route("/api/{rol}/chat", chat, methods=["POST"]),
        Route("/api/{rol}/confirmar", confirmar, methods=["POST"]),
        Route("/api/{rol}/reiniciar", reiniciar, methods=["POST"]),
        Mount("/static", StaticFiles(directory=ESTATICOS), name="static"),
    ],
    middleware=[Middleware(BaseHTTPMiddleware, dispatch=seguridad)],
    lifespan=lifespan,
    max_body_size=16_384,
)

if __name__ == "__main__":
    print(f"Web de {NOMBRE_BARBERIA}: http://{HOST}:{PUERTO}   Panel interno: http://{HOST}:{PUERTO}/panel   (Ctrl+C para parar)")
    uvicorn.run(app, host=HOST, port=PUERTO, log_level="warning")
