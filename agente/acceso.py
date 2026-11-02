"""Acceso al panel interno: contraseña con hash scrypt + sesiones en memoria.

Ejemplo:
    .env  ->  PANEL_CLAVE=scrypt:<sal>:<hash>     (lo genera: uv run python agente\\crear_clave.py)
    POST /api/login {"clave": "..."}  ->  cookie "sesion" (HttpOnly, SameSite=Strict)  ->  /panel se abre

Seguridad:
- La contraseña NUNCA se guarda: solo su hash scrypt con una sal aleatoria. scrypt es lento a propósito
  (y gasta memoria), así que probar millones de contraseñas contra un hash robado sale muy caro.
- La comparación es de tiempo constante (hmac.compare_digest): no da pistas por lo que tarda.
- La sesión es un token aleatorio de 256 bits que solo existe en la memoria del servidor: no se
  puede adivinar ni fabricar, caduca a las 8 horas y se borra al salir (o al reiniciar el servidor).
- Tras 5 fallos seguidos, el login se bloquea 60 segundos (frena a quien prueba contraseñas).
- Sin PANEL_CLAVE en el .env, el panel queda CERRADO (fallar cerrado, nunca abierto).
"""
import hashlib
import hmac
import os
import secrets
import time

# Coste de scrypt (los valores recomendados por OWASP para scrypt): ~50 ms y 16 MB por intento.
N, R, P = 2**14, 8, 1
DURACION_SESION = 8 * 3600  # segundos (una jornada)
MAX_FALLOS, BLOQUEO = 5, 60  # 5 fallos seguidos -> 60 s sin poder probar

_sesiones: dict[str, float] = {}  # token -> momento en que caduca
_fallos = {"seguidos": 0, "hasta": 0.0}


def hash_clave(clave: str, sal: bytes | None = None) -> str:
    """Ejemplo: hash_clave("cortes-2026") -> "scrypt:3f9a...:8b1c..." (cambia cada vez por la sal)."""
    sal = sal or secrets.token_bytes(16)
    h = hashlib.scrypt(clave.encode("utf-8"), salt=sal, n=N, r=R, p=P, maxmem=64 * 1024 * 1024)
    # Separador ":" y no "$": Docker Compose también lee el .env y trataría "$algo" como una variable.
    return f"scrypt:{sal.hex()}:{h.hex()}"


def configurada() -> bool:
    return os.environ.get("PANEL_CLAVE", "").startswith("scrypt:")


def clave_correcta(clave: str) -> bool:
    guardada = os.environ.get("PANEL_CLAVE", "")
    try:
        tipo, sal, _ = guardada.split(":")
        sal_bytes = bytes.fromhex(sal)
    except ValueError:
        return False  # mal configurada: cerrado
    if tipo != "scrypt":
        return False
    return hmac.compare_digest(hash_clave(clave, sal_bytes), guardada)


def segundos_bloqueado() -> int:
    return max(0, round(_fallos["hasta"] - time.monotonic()))


def registrar_fallo() -> None:
    _fallos["seguidos"] += 1
    if _fallos["seguidos"] >= MAX_FALLOS:
        _fallos["seguidos"] = 0
        _fallos["hasta"] = time.monotonic() + BLOQUEO


def reiniciar_fallos() -> None:
    _fallos["seguidos"] = 0


def crear_sesion() -> str:
    token = secrets.token_urlsafe(32)  # 256 bits aleatorios: imposible de adivinar
    _sesiones[token] = time.monotonic() + DURACION_SESION
    return token


def sesion_valida(token: str | None) -> bool:
    if not token:
        return False
    caduca = _sesiones.get(token)
    if caduca is None:
        return False
    if time.monotonic() > caduca:
        del _sesiones[token]
        return False
    return True


def cerrar_sesion(token: str | None) -> None:
    _sesiones.pop(token or "", None)
