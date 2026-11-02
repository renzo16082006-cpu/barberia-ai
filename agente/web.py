"""Web de chat de la barbería, encima del harness (agente/harness.py).

Arrancar:  uv run python agente\\web.py
  http://127.0.0.1:8000/       web pública de la barbería + asistente para CLIENTES (solo documentos)
  http://127.0.0.1:8000/panel  panel INTERNO del personal (todas las tools, confirma antes de escribir)
                               -> pide contraseña (/login); la crea agente\\crear_clave.py (ver acceso.py)

Seguridad:
- Solo escucha en 127.0.0.1: nadie de tu red (ni del wifi) puede entrar.
- Anti-CSRF: los POST a /api deben ser JSON y traer Origin = esta misma web. Así otra
  página que visites no puede mandar "confirmar" a tu asistente por detrás.
- Content-Security-Policy: el navegador solo ejecuta scripts servidos por esta web
  (por eso el JS va en un archivo aparte y no dentro del HTML).
- La página pinta las respuestas con textContent, nunca innerHTML: si el modelo
  devuelve HTML o un <script>, se ve como texto y no se ejecuta.
- Límites de tamaño (petición y mensaje) y errores internos sin detalles para el navegador.
- Login del panel: /panel y /api/interno/* se protegen AQUÍ, en el middleware (un solo sitio: una ruta
  nueva no se puede quedar sin proteger por olvido). Sin sesión: /panel -> /login y la API -> 401.
  Cookie de sesión HttpOnly (el JS no la lee) y SameSite=Strict (otra web no la puede usar).
  En producción, además: HTTPS y la cookie con Secure.
"""
import asyncio
import contextlib
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from harness import MODELO, NOMBRE_BARBERIA, Agente, Client, mcp
from server import BARBERIA_ID, conectar  # noqa: E402 (harness ya añadió mcp_server al path)

import acceso

HOST, PUERTO = "127.0.0.1", 8000
ORIGENES = {f"http://{HOST}:{PUERTO}", f"http://localhost:{PUERTO}"}
MAX_TEXTO = 1000  # caracteres por mensaje
ESTATICOS = Path(__file__).resolve().parent / "static"

ROLES_WEB = {"cliente", "interno"}
COOKIE = "sesion"
agentes = {}  # una conversación por rol (demo local)
candado = asyncio.Lock()  # una petición cada vez: el agente no se mezcla


@contextlib.asynccontextmanager
async def lifespan(app):
    async with Client(mcp) as client:
        for rol in ROLES_WEB:
            agentes[rol] = await Agente.crear(client, rol)
        yield


def logueado(request: Request) -> bool:
    return acceso.sesion_valida(request.cookies.get(COOKIE))


async def seguridad(request: Request, call_next):
    ruta = request.url.path
    if ruta.startswith("/api/") and request.method == "POST":
        if request.headers.get("origin") not in ORIGENES:
            return JSONResponse({"error": "Origen no permitido"}, status_code=403)
        if not request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"error": "Se esperaba JSON"}, status_code=415)
    if (ruta == "/panel" or ruta.startswith("/api/interno/")) and not logueado(request):
        if ruta == "/panel":
            respuesta = RedirectResponse("/login", status_code=303)
        else:
            respuesta = JSONResponse({"tipo": "error", "texto": "Inicia sesión para usar el panel.",
                                      "traza": []}, status_code=401)
    else:
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
    rol = request.path_params["rol"]
    if rol == "interno" and not logueado(request):  # segunda capa (la primera es el middleware)
        return None
    return agentes.get(rol)  # None si el rol no existe


async def pagina_login(request: Request):
    if logueado(request):
        return RedirectResponse("/panel", status_code=303)
    return FileResponse(ESTATICOS / "login.html")


async def login(request: Request):
    espera = acceso.segundos_bloqueado()
    if espera:
        return error(f"Demasiados intentos fallidos. Espera {espera} s.", 429)
    if not acceso.configurada():  # fallar CERRADO: sin contraseña configurada no entra nadie
        return error("El panel aún no tiene contraseña: créala con agente\\crear_clave.py (mira el README).", 503)
    clave = (await leer_json(request)).get("clave")
    if not isinstance(clave, str) or not 1 <= len(clave) <= 200:
        return error("Escribe la contraseña.")
    if not await asyncio.to_thread(acceso.clave_correcta, clave):  # scrypt tarda: fuera del bucle principal
        acceso.registrar_fallo()
        return error("Contraseña incorrecta.", 401)
    acceso.reiniciar_fallos()
    respuesta = JSONResponse({"ok": True})
    # Token NUEVO en cada login (nadie puede "plantar" una sesión antes). HttpOnly: el JS no la lee.
    # SameSite=Strict: el navegador no la envía en peticiones que vengan de otra web.
    respuesta.set_cookie(COOKIE, acceso.crear_sesion(), max_age=acceso.DURACION_SESION,
                         httponly=True, samesite="strict", path="/")
    return respuesta


async def logout(request: Request):
    acceso.cerrar_sesion(request.cookies.get(COOKIE))
    async with candado:  # la siguiente persona no hereda la conversación del panel
        viejo = agentes["interno"]
        agentes["interno"] = Agente(viejo.client, viejo.todas, "interno")
    respuesta = JSONResponse({"ok": True})
    respuesta.delete_cookie(COOKIE, path="/")
    return respuesta


async def info(request: Request):
    return JSONResponse({"barberia": NOMBRE_BARBERIA, "modelo": MODELO})


def leer_horario() -> dict:
    """Horario de ESTA barberia (tabla horarios). Dias ISO: 1 = lunes ... 7 = domingo; sin fila = cerrado.
    Ejemplo: {"1": ["10:00", "20:00"], "6": ["09:00", "14:00"]}"""
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT dia_semana, abre, cierra FROM horarios WHERE barberia_id = %s ORDER BY dia_semana",
                    (BARBERIA_ID,))
        return {str(dia): [f"{abre:%H:%M}", f"{cierra:%H:%M}"] for dia, abre, cierra in cur.fetchall()}


async def horario(request: Request):
    # Una sola fuente de verdad: la misma tabla que usan huecos_libres y crear_cita.
    try:
        return JSONResponse({"horario": await asyncio.to_thread(leer_horario)})
    except Exception as e:  # el detalle a la terminal, no al navegador
        print("ERROR:", repr(e))
        return error("No se ha podido leer el horario.", 500)


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
        Route("/login", pagina_login),
        Route("/api/login", login, methods=["POST"]),
        Route("/api/logout", logout, methods=["POST"]),
        Route("/api/info", info),
        Route("/api/horario", horario),
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
