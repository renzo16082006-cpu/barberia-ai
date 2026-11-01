# 💈 Barbería IA

CRM para barberías con una serie de proyectos de IA construidos encima.
Datos de prueba inventados. Proyecto de portfolio de **Renzo Povis** (DAM, Tarragona).

## Qué hay ahora (Proyecto 0: CRM base)

- **PostgreSQL 18 + pgvector** en Docker (+ Adminer para verlo en el navegador).
- 6 tablas: `barberias`, `barberos`, `clientes`, `servicios`, `citas`, `ventas`.
- **Aislamiento entre negocios en la propia base de datos**: todas las tablas llevan `barberia_id`
  y las citas/ventas usan **claves foráneas compuestas** `(barberia_id, id)`.
  Una cita de la barbería 1 con un barbero de la barbería 2 es **rechazada por Postgres**,
  aunque el error venga de un agente de IA.
- Reglas en la BD: `CHECK` en precios, duraciones, estados y métodos de pago; dinero en `NUMERIC(8,2)`.

## Seguridad

- Secretos en `.env` (fuera de Git); plantilla en `.env.example`.
- Postgres y Adminer solo escuchan en `127.0.0.1`.

## Cómo arrancarlo

```powershell
git clone https://github.com/renzo16082006-cpu/barberia-ai.git
cd barberia-ai
Copy-Item .env.example .env      # y cambia POSTGRES_PASSWORD
docker compose up -d
Get-ChildItem db\*.sql | ForEach-Object { Get-Content $_ | docker exec -i barberia-db psql -U barberia -v ON_ERROR_STOP=1 }
```

Adminer: http://localhost:8080 (Sistema PostgreSQL, Servidor `db`, usuario `barberia`).

## Hoja de ruta

- [x] **0. CRM base**: Postgres 18 + pgvector, permisos por negocio
- [ ] **1. Servidor MCP** con FastMCP (Python) para consultar el CRM desde Claude
- [ ] **2. RAG** con pgvector, sin framework, con citas y respuesta "no lo sé"
- [ ] **3. Evals** con promptfoo: modelo local (Ollama) vs Claude Haiku vs Opus
- [ ] **4. Harness de agente propio**: bucle con tools, límite de pasos y confirmación antes de escribir
- [ ] **5. Memoria del agente**: primero propia, luego mem0, vía MCP
