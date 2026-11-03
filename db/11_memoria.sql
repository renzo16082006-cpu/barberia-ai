-- Memoria del agente (Proyecto 5): lo que el personal le pide recordar de cada cliente.
-- Una fila por dato, con su fecha, para poder ver cuando se guardo y olvidar uno concreto.
-- Ejemplo: (1, 1, 'Quiere el degradado mas bajo; no le gusta hablar de futbol')
--          = El Navajas, Pedro Ruiz, un dato.
CREATE TABLE IF NOT EXISTS memoria (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barberia_id  BIGINT NOT NULL REFERENCES barberias(id) ON DELETE CASCADE,
    cliente_id   BIGINT NOT NULL,
    dato         TEXT NOT NULL CHECK (char_length(dato) BETWEEN 3 AND 300),
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Clave foranea compuesta: el cliente TIENE que ser de la misma barberia.
    -- Guardar un dato de un cliente de Corte Fino con barberia_id = 1 lo rechaza Postgres.
    -- ON DELETE CASCADE: si se borra el cliente, se borra lo que se recordaba de el.
    FOREIGN KEY (barberia_id, cliente_id) REFERENCES clientes (barberia_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memoria_cliente ON memoria (barberia_id, cliente_id);
