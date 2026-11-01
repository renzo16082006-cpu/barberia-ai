# 💈 Barbería IA

CRM para barberías con una serie de proyectos de IA construidos encima.
Datos de prueba inventados. Proyecto de portfolio de **Renzo Povis** (DAM, Tarragona).

> **Tú, en Claude Desktop:** ¿Tiene Pedro alguna cita pendiente esta semana?
> **Claude** *(llama a `citas_de_cliente`)*: Sí, el miércoles 4 a las 10:00, corte clásico con Miguel.
> Recuérdale a Miguel que Pedro no quiere la máquina del 0.

## Hoja de ruta

- [x] **0. CRM base**: Postgres 18 + pgvector en Docker, permisos por negocio
- [x] **1. Servidor MCP** con FastMCP 4 (Python): Claude consulta y gestiona el CRM
- [ ] **2. RAG** con pgvector, sin framework, con citas y respuesta "no lo sé"
- [ ] **3. Evals** con promptfoo: modelo local (Ollama) vs Claude Haiku vs Opus
- [ ] **4. Harness de agente propio**: bucle con tools, límite de pasos y confirmación antes de escribir
- [ ] **5. Memoria del agente**: primero propia, luego mem0, vía MCP

## Proyecto 0: CRM base

- **PostgreSQL 18 + pgvector** en Docker, con Adminer para verlo en el navegador.
- 6 tablas: `barberias`, `barberos`, `clientes`, `servicios`, `citas`, `ventas`.
- **Aislamiento entre negocios en la propia base de datos**: todas las tablas llevan `barberia_id`
  y las citas y ventas usan **claves foráneas compuestas** `(barberia_id, id)`.
  Una cita de la barbería 1 con un barbero de la barbería 2 la **rechaza Postgres**.
- Reglas en la BD: `CHECK` en precios, duraciones, estados y métodos de pago; dinero en `NUMERIC(8,2)`.

## Proyecto 1: Servidor MCP

Servidor [MCP](https://modelcontextprotocol.io) en Python con **FastMCP 4** y **psycopg 3**.

| Tool | Tipo | Qué hace |
|---|---|---|
| `citas_del_dia(fecha)` | Lectura | Agenda de un día |
| `buscar_cliente(nombre)` | Lectura | Ficha del cliente: teléfono, notas, nº de citas, última visita |
| `citas_de_cliente(nombre, solo_futuras)` | Lectura | Próximas citas o historial de un cliente |
| `resumen_ventas(desde, hasta)` | Lectura | Total facturado y desglose por método de pago |
| `crear_cita(cliente, barbero, servicio, inicio)` | **Escritura** | Crea una cita pendiente |
| `cancelar_cita(cita_id)` | **Escritura** | Cancela sin borrar (queda el historial) |

### Capturas

**Claude usa el servidor y razona con los datos** (detecta una posible cita duplicada):

![Solicitud y respuesta del servidor](docs/capturas/01a-citas-pedro-json.png)
![Respuesta de Claude](docs/capturas/01b-citas-pedro-respuesta.png)

**Intento de suplantación**: Claude intenta volcar todos los clientes y el servidor lo bloquea:

![Intento bloqueado por el servidor](docs/capturas/02a-suplantacion-intento.png)
![Respuesta de Claude](docs/capturas/02b-suplantacion-respuesta.png)

**Validaciones al escribir**: solape de horario y fecha pasada:

![Errores de validación](docs/capturas/03a-validaciones-errores.png)
![Respuesta de Claude](docs/capturas/03b-validaciones-respuesta.png)
### Decisiones de seguridad

- **La IA no elige la barbería.** `BARBERIA_ID` se fija en el servidor (`.env`); ninguna tool
  tiene ese parámetro. Pedir datos de otro negocio no tiene ningún camino técnico.
- **SQL siempre parametrizado** (`%s`). Probado con `'; DROP TABLE clientes; --`.
- **Sin enumeración**: búsquedas por nombre con mínimo 2 caracteres, `%` y `_` escapados y `LIMIT`.
- **Validación en el servidor, no en el modelo**: fechas futuras, rango de fechas coherente,
  nombres que coinciden con un único resultado, barbero y servicio activos, sin solapes.
- **Concurrencia**: `SELECT ... FOR UPDATE` sobre el barbero al reservar, dentro de una transacción.
- **No revelar lo ajeno**: cancelar una cita de otra barbería responde "No existe la cita".
- Respuestas siempre como objeto e indicando la barbería, para que el modelo no confunda de quién son los datos.

Varias de estas mejoras salieron de pedirle a Claude que **probara y criticara** el servidor
(formato de respuesta inconsistente, enumeración con `%`, búsquedas con tildes).

## Cómo arrancarlo

Requisitos: Docker, Python 3.13 y [uv](https://docs.astral.sh/uv/).

```powershell
git clone https://github.com/renzo16082006-cpu/barberia-ai.git
cd barberia-ai
Copy-Item .env.example .env      # y cambia POSTGRES_PASSWORD
docker compose up -d
Get-ChildItem db\*.sql | ForEach-Object { Get-Content $_ | docker exec -i barberia-db psql -U barberia -v ON_ERROR_STOP=1 }
uv sync
uv run python mcp_server\probar.py
```

Adminer: http://localhost:8080 (Sistema PostgreSQL, Servidor `db`, usuario `barberia`).

### Conectarlo a Claude Desktop

En *Ajustes → Desarrollador → Editar configuración* (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "barberia": {
      "command": "C:\\ruta\\a\\uv.exe",
      "args": ["run", "--directory", "C:\\ruta\\a\\barberia-ai", "python", "mcp_server\\server.py"]
    }
  }
}
```
