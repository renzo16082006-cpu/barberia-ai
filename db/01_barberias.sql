-- Tabla principal: cada negocio (tenant) del CRM
CREATE TABLE IF NOT EXISTS barberias (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre     TEXT NOT NULL,
    ciudad     TEXT,
    creado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);
