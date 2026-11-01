"""Servidor MCP del CRM de la barbería (Proyecto 1)."""
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

# Opción B: la barbería la fija el servidor (.env), NUNCA la IA.
BARBERIA_ID = int(os.environ["BARBERIA_ID"])
MADRID = ZoneInfo("Europe/Madrid")

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


def patron_nombre(nombre: str) -> str:
    """Prepara el texto de busqueda para ILIKE de forma segura:
    exige 2 o mas caracteres y escapa los comodines % y _."""
    nombre = nombre.strip()
    if len(nombre) < 2:
        raise ValueError("Escribe al menos 2 letras del nombre")
    escapado = nombre.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"

def cargar_nombre_barberia() -> str:
    """Lee el nombre de la barberia configurada. Si BARBERIA_ID no existe,
    el servidor no arranca: mejor fallar al inicio que dar datos raros."""
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT nombre FROM barberias WHERE id = %s", (BARBERIA_ID,))
        fila = cur.fetchone()
    if fila is None:
        raise RuntimeError(f"No existe ninguna barberia con id {BARBERIA_ID}")
    return fila[0]


NOMBRE_BARBERIA = cargar_nombre_barberia()

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
        return {"barberia": NOMBRE_BARBERIA, "fecha": str(fecha), "citas": cur.fetchall()}


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
          AND unaccent(cl.nombre) ILIKE unaccent(%s)
        GROUP BY cl.id
        ORDER BY cl.nombre
        LIMIT 10
    """
    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (BARBERIA_ID, patron_nombre(nombre)))
        return {"barberia": NOMBRE_BARBERIA, "busqueda": nombre, "clientes": cur.fetchall()}


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
          AND unaccent(cl.nombre) ILIKE unaccent(%s)
          AND (NOT %s OR c.inicio >= now())
        ORDER BY c.inicio
        LIMIT 20
    """
    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (BARBERIA_ID, patron_nombre(nombre), solo_futuras))
        return {"barberia": NOMBRE_BARBERIA, "busqueda": nombre, "solo_futuras": solo_futuras, "citas": cur.fetchall()}


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
    return {"barberia": NOMBRE_BARBERIA, "desde": str(desde), "hasta": str(hasta), **totales, "por_metodo_pago": por_metodo}


def buscar_uno(cur, sql: str, nombre: str) -> dict:
    """Busca por nombre en esta barberia y exige UN solo resultado."""
    cur.execute(sql, (BARBERIA_ID, patron_nombre(nombre)))
    filas = cur.fetchall()
    if not filas:
        raise ValueError(f"No encuentro nada que coincida con '{nombre}'")
    if len(filas) > 1:
        opciones = ", ".join(f["nombre"] for f in filas)
        raise ValueError(f"'{nombre}' coincide con varios: {opciones}. Di cual exactamente.")
    return filas[0]


@mcp.tool
def crear_cita(cliente: str, barbero: str, servicio: str, inicio: datetime) -> dict:
    """ESCRIBE en la base de datos: crea una cita en estado 'pendiente'.
    Antes de llamarla, confirma con el usuario cliente, barbero, servicio, dia y hora.
    cliente, barbero y servicio: nombre o parte del nombre (debe coincidir con uno solo).
    inicio: fecha y hora en hora de Espana, formato AAAA-MM-DDTHH:MM.
    Rechaza fechas pasadas, barberos o servicios inactivos y solapes con otra cita del barbero."""
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=MADRID)
    if inicio <= datetime.now(MADRID):
        raise ValueError("La cita tiene que ser en el futuro")

    with conectar() as conn, conn.cursor(row_factory=dict_row) as cur:
        cli = buscar_uno(cur, "SELECT id, nombre FROM clientes "
                              "WHERE barberia_id = %s AND unaccent(nombre) ILIKE unaccent(%s)", cliente)
        bar = buscar_uno(cur, "SELECT id, nombre FROM barberos "
                              "WHERE barberia_id = %s AND activo AND unaccent(nombre) ILIKE unaccent(%s)", barbero)
        ser = buscar_uno(cur, "SELECT id, nombre, duracion_min FROM servicios "
                              "WHERE barberia_id = %s AND activo AND unaccent(nombre) ILIKE unaccent(%s)", servicio)

        # Bloquea al barbero: si llegan dos reservas a la vez, la segunda espera a la primera.
        cur.execute("SELECT id FROM barberos WHERE id = %s FOR UPDATE", (bar["id"],))

        fin = inicio + timedelta(minutes=ser["duracion_min"])
        cur.execute("""
            SELECT to_char(c.inicio AT TIME ZONE 'Europe/Madrid', 'YYYY-MM-DD HH24:MI') AS inicio,
                   s.nombre AS servicio
            FROM citas c
            JOIN servicios s ON s.id = c.servicio_id
            WHERE c.barberia_id = %s
              AND c.barbero_id = %s
              AND c.estado <> 'cancelada'
              AND c.inicio < %s
              AND c.inicio + make_interval(mins => s.duracion_min) > %s
        """, (BARBERIA_ID, bar["id"], fin, inicio))
        choque = cur.fetchone()
        if choque:
            raise ValueError(f"{bar['nombre']} ya tiene una cita a esa hora: "
                             f"{choque['servicio']} el {choque['inicio']}")

        cur.execute("""
            INSERT INTO citas (barberia_id, cliente_id, barbero_id, servicio_id, inicio)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (BARBERIA_ID, cli["id"], bar["id"], ser["id"], inicio))
        cita_id = cur.fetchone()["id"]

    return {"barberia": NOMBRE_BARBERIA, "cita_creada": {
        "id": cita_id, "cliente": cli["nombre"], "barbero": bar["nombre"],
        "servicio": ser["nombre"], "inicio": inicio.strftime("%Y-%m-%d %H:%M"),
        "fin": fin.strftime("%H:%M"), "estado": "pendiente"}}

if __name__ == "__main__":
    mcp.run()
