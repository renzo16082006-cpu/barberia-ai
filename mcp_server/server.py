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
def citas_del_dia(fecha: date) -> dict:
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
        return {"fecha": str(fecha), "citas": cur.fetchall()}


@mcp.tool
def buscar_cliente(nombre: str) -> dict:
    """Busca clientes de la barbería por nombre o parte del nombre (sin
    distinguir mayúsculas). Devuelve nombre, teléfono, notas, número de
    citas y fecha de la última visita completada."""
    sql = """
        SELECT cl.nombre,
               cl.telefono,
               cl.notas,
               count(c.id) AS num_citas,
               to_char((max(c.inicio) FILTER (WHERE c.estado = 'completada'))
                       AT TIME ZONE 'Europe/Madrid', 'YYYY-MM-DD') AS ultima_visita
        FROM clientes cl
        LEFT JOIN citas c ON c.cliente_id = cl.id AND c.barberia_id = cl.barberia_id
        WHERE cl.barberia_id = %s
          AND cl.nombre ILIKE %s
        GROUP BY cl.id
        ORDER BY cl.nombre
        LIMIT 10
    """
    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (BARBERIA_ID, f"%{nombre}%"))
        return {"busqueda": nombre, "clientes": cur.fetchall()}


@mcp.tool
def citas_de_cliente(nombre: str, solo_futuras: bool = True) -> dict:
    """Busca las citas de un cliente por nombre o parte del nombre (sin
    distinguir mayusculas). Por defecto solo las futuras; con
    solo_futuras=False devuelve tambien el historial. Maximo 20 citas."""
    sql = """
        SELECT cl.nombre AS cliente,
               to_char(c.inicio AT TIME ZONE 'Europe/Madrid', 'YYYY-MM-DD') AS fecha,
               to_char(c.inicio AT TIME ZONE 'Europe/Madrid', 'HH24:MI')    AS hora,
               b.nombre AS barbero,
               s.nombre AS servicio,
               c.estado
        FROM citas c
        JOIN clientes  cl ON cl.id = c.cliente_id
        JOIN barberos  b  ON b.id  = c.barbero_id
        JOIN servicios s  ON s.id  = c.servicio_id
        WHERE c.barberia_id = %s
          AND cl.nombre ILIKE %s
          AND (NOT %s OR c.inicio >= now())
        ORDER BY c.inicio
        LIMIT 20
    """
    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (BARBERIA_ID, f"%{nombre}%", solo_futuras))
        return {"busqueda": nombre, "solo_futuras": solo_futuras, "citas": cur.fetchall()}


@mcp.tool
def resumen_ventas(desde: date, hasta: date) -> dict:
    """Resumen de ventas de la barberia entre dos fechas, ambas incluidas
    (formato AAAA-MM-DD): numero de ventas, total facturado y desglose por
    metodo de pago. Los importes van en euros como texto con 2 decimales."""
    if desde > hasta:
        raise ValueError("'desde' no puede ser posterior a 'hasta'")
    filtro = """
        FROM ventas v
        WHERE v.barberia_id = %s
          AND (v.fecha AT TIME ZONE 'Europe/Madrid')::date BETWEEN %s AND %s
    """
    params = (BARBERIA_ID, desde, hasta)
    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT count(*) AS num_ventas, coalesce(sum(v.importe), 0)::text AS total"
                    + filtro, params)
        totales = cur.fetchone()
        cur.execute("SELECT v.metodo_pago, count(*) AS num_ventas, sum(v.importe)::text AS total"
                    + filtro + " GROUP BY v.metodo_pago ORDER BY v.metodo_pago", params)
        por_metodo = cur.fetchall()
    return {"desde": str(desde), "hasta": str(hasta), **totales, "por_metodo_pago": por_metodo}


if __name__ == "__main__":
    mcp.run()
