"""Crea la contraseña del panel interno y te dice la línea que tienes que poner en el .env.

Uso:  uv run python agente\\crear_clave.py

La contraseña se escribe sin que se vea en pantalla, y lo que se guarda en el .env es solo su
hash (scrypt:<sal>:<hash>), nunca la contraseña. Para cambiarla, vuelve a ejecutar este script.
"""
from getpass import getpass

from acceso import hash_clave

MINIMO = 10  # caracteres: una frase corta es más fácil de recordar y más difícil de adivinar


def main():
    print(f"Contraseña del panel interno (mínimo {MINIMO} caracteres; no se verá al escribir).")
    clave = getpass("Contraseña: ")
    if len(clave) < MINIMO:
        print(f"Demasiado corta: usa al menos {MINIMO} caracteres. No se ha cambiado nada.")
        return
    if getpass("Repítela: ") != clave:
        print("No coinciden. No se ha cambiado nada.")
        return
    print("\nAñade (o cambia) esta línea en tu archivo .env y reinicia la web:\n")
    print(f"PANEL_CLAVE={hash_clave(clave)}")


if __name__ == "__main__":
    main()
