-- 1) Permitir referenciar la pareja (barberia_id, id) en las otras tablas
ALTER TABLE barberos  ADD CONSTRAINT barberos_barberia_id_uk  UNIQUE (barberia_id, id);
ALTER TABLE clientes  ADD CONSTRAINT clientes_barberia_id_uk  UNIQUE (barberia_id, id);
ALTER TABLE servicios ADD CONSTRAINT servicios_barberia_id_uk UNIQUE (barberia_id, id);

-- 2) Citas: barbero, cliente y servicio SIEMPRE de la misma barberia
CREATE TABLE IF NOT EXISTS citas (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barberia_id  BIGINT NOT NULL REFERENCES barberias(id) ON DELETE CASCADE,
    cliente_id   BIGINT NOT NULL,
    barbero_id   BIGINT NOT NULL,
    servicio_id  BIGINT NOT NULL,
    inicio       TIMESTAMPTZ NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'pendiente'
                 CHECK (estado IN ('pendiente','confirmada','completada','cancelada')),
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (barberia_id, cliente_id)  REFERENCES clientes  (barberia_id, id),
    FOREIGN KEY (barberia_id, barbero_id)  REFERENCES barberos  (barberia_id, id),
    FOREIGN KEY (barberia_id, servicio_id) REFERENCES servicios (barberia_id, id)
);

CREATE INDEX IF NOT EXISTS idx_citas_barberia_inicio ON citas (barberia_id, inicio);
