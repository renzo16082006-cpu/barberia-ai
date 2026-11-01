-- Clientes: cada barberia tiene su propia lista
CREATE TABLE IF NOT EXISTS clientes (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barberia_id  BIGINT NOT NULL REFERENCES barberias(id) ON DELETE CASCADE,
    nombre       TEXT NOT NULL,
    telefono     TEXT,
    email        TEXT,
    notas        TEXT,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (barberia_id, telefono)
);
