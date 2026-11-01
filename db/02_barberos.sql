-- Barberos: cada uno pertenece a UNA barberia
CREATE TABLE IF NOT EXISTS barberos (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barberia_id  BIGINT NOT NULL REFERENCES barberias(id) ON DELETE CASCADE,
    nombre       TEXT NOT NULL,
    telefono     TEXT,
    activo       BOOLEAN NOT NULL DEFAULT true,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_barberos_barberia ON barberos (barberia_id);
