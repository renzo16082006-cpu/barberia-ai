"""Servidor MCP del CRM de la barbería (Proyecto 1)."""
import os
from datetime import date

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

# Opción B: la barbería la fija el servidor (.env), NUNCA la IA.
BARBERIA_ID = int(os.environ["BARBERIA_ID"])

mcp = FastMCP("Barbería IA")


def conectar():
    """Abre una conexión a Postgres con los datos del .env."""
    return psycopg.connect(
        host="127.0.0.1",
        port=5432,
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


@mcp.tool
def citas_del_dia(fecha: date) -> list[dict]:
    """Devuelve las citas de la barbería para un día (formato AAAA-MM-DD):
    hora, cliente, barbero, servicio y estado."""
    sql = """
        SELECT to_char(c.inicio AT TIME ZONE 'Europe/Madrid', 'HH24:MI') AS hora,
               cl.nombre AS cliente,
               b.nombre  AS barbero,
               s.nombre  AS servicio,
               c.estado
        FROM citas c
        JOIN clientes  cl ON cl.id = c.cliente_id
        JOIN barberos  b  ON b.id  = c.barbero_id
        JOIN servicios s  ON s.id  = c.servicio_id
        WHERE c.barberia_id = %s
          AND (c.inicio AT TIME ZONE 'Europe/Madrid')::date = %s
        ORDER BY c.inicio
    """
    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (BARBERIA_ID, fecha))
        return cur.fetchall()


if __name__ == "__main__":
    mcp.run()
