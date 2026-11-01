"""Carga los documentos en Postgres: trocea, calcula embeddings con Ollama y guarda."""
import json
import os
import urllib.request

import psycopg
from dotenv import load_dotenv

from trocear import CARPETA, trocear

load_dotenv()

MODELO = "bge-m3"
OLLAMA_URL = "http://localhost:11434/api/embed"

# Carpeta de documentos -> id de la barberia en la base de datos
BARBERIAS = {"el-navajas": 1, "corte-fino": 2}


def embeddings(textos: list[str]) -> list[list[float]]:
    """Pide a Ollama (en este PC) un vector por cada texto."""
    peticion = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({"model": MODELO, "input": textos}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        return json.load(respuesta)["embeddings"]


def como_vector(numeros: list[float]) -> str:
    """pgvector acepta los vectores como texto: '[0.1,0.2,...]'."""
    return "[" + ",".join(str(n) for n in numeros) + "]"


def conectar():
    return psycopg.connect(
        host="127.0.0.1",
        port=5432,
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def main():
    with conectar() as conn, conn.cursor() as cur:
        for archivo in sorted(CARPETA.glob("*/*.md")):
            if archivo.parent.name not in BARBERIAS:
                raise SystemExit(f"Carpeta sin barberia asignada: {archivo.parent.name}")
            barberia_id = BARBERIAS[archivo.parent.name]

            titulo, trozos = trocear(archivo.read_text(encoding="utf-8-sig"))
            textos = [f"{titulo} > {t['seccion']}\n{t['contenido']}" for t in trozos]
            vectores = embeddings(textos)

            # Si el documento ya estaba cargado, se borra (y sus trozos, por el CASCADE) y se vuelve a cargar
            cur.execute("DELETE FROM documentos WHERE barberia_id = %s AND fuente = %s",
                        (barberia_id, archivo.name))
            cur.execute("INSERT INTO documentos (barberia_id, titulo, fuente) "
                        "VALUES (%s, %s, %s) RETURNING id",
                        (barberia_id, titulo, archivo.name))
            documento_id = cur.fetchone()[0]

            for orden, (trozo, vector) in enumerate(zip(trozos, vectores), 1):
                cur.execute("""
                    INSERT INTO documento_chunks
                        (barberia_id, documento_id, orden, seccion, contenido, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector)
                """, (barberia_id, documento_id, orden, trozo["seccion"],
                      trozo["contenido"], como_vector(vector)))

            print(f"{archivo.parent.name}/{archivo.name}: {len(trozos)} trozos cargados")


if __name__ == "__main__":
    main()
