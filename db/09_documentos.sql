-- RAG: documentos de cada barberia, troceados y con su embedding (bge-m3 = 1024 dimensiones)
CREATE TABLE IF NOT EXISTS documentos (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barberia_id  BIGINT NOT NULL REFERENCES barberias(id) ON DELETE CASCADE,
    titulo       TEXT NOT NULL,
    fuente       TEXT NOT NULL,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (barberia_id, fuente),
    UNIQUE (barberia_id, id)
);

CREATE TABLE IF NOT EXISTS documento_chunks (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barberia_id   BIGINT NOT NULL,
    documento_id  BIGINT NOT NULL,
    orden         INTEGER NOT NULL,
    seccion       TEXT,
    contenido     TEXT NOT NULL,
    embedding     vector(1024) NOT NULL,
    FOREIGN KEY (barberia_id, documento_id)
        REFERENCES documentos (barberia_id, id) ON DELETE CASCADE,
    UNIQUE (documento_id, orden)
);

CREATE INDEX IF NOT EXISTS idx_chunks_barberia ON documento_chunks (barberia_id);
