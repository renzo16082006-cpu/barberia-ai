"""Trocea los documentos Markdown por secciones (## ...)."""
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "documentos"


def trocear(texto: str) -> tuple[str, list[dict]]:
    """Devuelve el titulo (# ...) y una lista de trozos, uno por seccion (## ...)."""
    titulo = ""
    trozos = []
    seccion = None
    lineas = []

    def cerrar_seccion():
        contenido = "\n".join(lineas).strip()
        if seccion and contenido:
            trozos.append({"seccion": seccion, "contenido": contenido})

    for linea in texto.splitlines():
        if linea.startswith("# "):
            titulo = linea[2:].strip()
        elif linea.startswith("## "):
            cerrar_seccion()
            seccion = linea[3:].strip()
            lineas = []
        else:
            lineas.append(linea)
    cerrar_seccion()
    return titulo, trozos


if __name__ == "__main__":
    for archivo in sorted(CARPETA.glob("*/*.md")):
        titulo, trozos = trocear(archivo.read_text(encoding="utf-8-sig"))
        print(f"\n=== {archivo.parent.name}/{archivo.name}: {titulo} ({len(trozos)} trozos)")
        for i, trozo in enumerate(trozos, 1):
            print(f"  {i}. [{trozo['seccion']}] {trozo['contenido'][:60]}...")
