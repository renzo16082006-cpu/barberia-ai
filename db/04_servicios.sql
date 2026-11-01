-- Servicios: el menu de cada barberia (precio y duracion)
CREATE TABLE IF NOT EXISTS servicios (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barberia_id   BIGINT NOT NULL REFERENCES barberias(id) ON DELETE CASCADE,
    nombre        TEXT NOT NULL,
    duracion_min  INTEGER NOT NULL CHECK (duracion_min > 0),
    precio        NUMERIC(8,2) NOT NULL CHECK (precio >= 0),
    activo        BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (barberia_id, nombre)
);
