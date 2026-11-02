-- Horarios de apertura: una fila por barberia y dia de la semana.
-- dia_semana sigue la norma ISO (la misma que EXTRACT(ISODOW) de Postgres): 1 = lunes ... 7 = domingo.
-- Un dia SIN fila = cerrado. Simplificacion: un solo tramo por dia (sin cierre a mediodia).
-- Ejemplo: (1, 6, '09:00', '14:00') = El Navajas, sabado, de 9:00 a 14:00.
CREATE TABLE IF NOT EXISTS horarios (
    barberia_id  BIGINT NOT NULL REFERENCES barberias(id) ON DELETE CASCADE,
    dia_semana   SMALLINT NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),
    abre         TIME NOT NULL,
    cierra       TIME NOT NULL,
    PRIMARY KEY (barberia_id, dia_semana),   -- como mucho un horario por dia y barberia
    CHECK (cierra > abre)
);

-- Los mismos horarios que dicen los documentos del RAG (documentos/*/horarios*.md).
-- ON CONFLICT DO NOTHING: si se ejecuta dos veces, no duplica ni falla.
INSERT INTO horarios (barberia_id, dia_semana, abre, cierra) VALUES
  -- El Navajas (id 1): lunes a viernes 10:00-20:00, sabado 9:00-14:00
  (1, 1, '10:00', '20:00'),
  (1, 2, '10:00', '20:00'),
  (1, 3, '10:00', '20:00'),
  (1, 4, '10:00', '20:00'),
  (1, 5, '10:00', '20:00'),
  (1, 6, '09:00', '14:00'),
  -- Corte Fino (id 2): martes a sabado 10:00-18:00
  (2, 2, '10:00', '18:00'),
  (2, 3, '10:00', '18:00'),
  (2, 4, '10:00', '18:00'),
  (2, 5, '10:00', '18:00'),
  (2, 6, '10:00', '18:00')
ON CONFLICT DO NOTHING;
