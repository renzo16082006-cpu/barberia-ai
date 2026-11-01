-- Permitir referenciar la pareja (barberia_id, id) de citas
ALTER TABLE citas ADD CONSTRAINT citas_barberia_id_uk UNIQUE (barberia_id, id);

-- Ventas: servicios cobrados o productos sueltos
CREATE TABLE IF NOT EXISTS ventas (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barberia_id  BIGINT NOT NULL REFERENCES barberias(id) ON DELETE CASCADE,
    cita_id      BIGINT,
    cliente_id   BIGINT,
    concepto     TEXT NOT NULL,
    importe      NUMERIC(8,2) NOT NULL CHECK (importe >= 0),
    metodo_pago  TEXT NOT NULL CHECK (metodo_pago IN ('efectivo','tarjeta','bizum')),
    fecha        TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (barberia_id, cita_id)    REFERENCES citas    (barberia_id, id),
    FOREIGN KEY (barberia_id, cliente_id) REFERENCES clientes (barberia_id, id)
);

CREATE INDEX IF NOT EXISTS idx_ventas_barberia_fecha ON ventas (barberia_id, fecha);
