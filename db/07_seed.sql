-- Datos de prueba (inventados). Ejecutar UNA vez sobre la BD recien creada.
BEGIN;

INSERT INTO barberias (nombre, ciudad) VALUES
  ('El Navajas', 'Tarragona'),   -- id 1
  ('Corte Fino', 'Reus');        -- id 2

INSERT INTO barberos (barberia_id, nombre, telefono) VALUES
  (1, 'Carlos', '611000001'),    -- id 1
  (1, 'Miguel', '611000002'),    -- id 2
  (2, 'Jordi',  '611000003'),    -- id 3
  (2, 'Ana',    '611000004');    -- id 4

INSERT INTO clientes (barberia_id, nombre, telefono, notas) VALUES
  (1, 'Pedro Ruiz',  '600111222', 'Degradado bajo. No usar maquina del 0.'),       -- id 1
  (1, 'Luis Gomez',  '600333444', 'Siempre pide a Carlos. Barba larga.'),          -- id 2
  (1, 'Marc Puig',   '600555666', 'Piel sensible: aftershave sin alcohol.'),       -- id 3
  (2, 'Pedro Ruiz',  '600111222', 'Viene cada 3 semanas, corte clasico.'),         -- id 4
  (2, 'Sergi Vidal', '600777888', 'Prefiere citas por la tarde.');                 -- id 5

INSERT INTO servicios (barberia_id, nombre, duracion_min, precio) VALUES
  (1, 'Corte clasico',    30, 15.00),  -- id 1
  (1, 'Corte + barba',    45, 22.50),  -- id 2
  (1, 'Arreglo de barba', 20, 10.00),  -- id 3
  (2, 'Corte clasico',    25, 13.00),  -- id 4
  (2, 'Corte + barba',    40, 20.00);  -- id 5

INSERT INTO citas (barberia_id, cliente_id, barbero_id, servicio_id, inicio, estado) VALUES
  (1, 1, 1, 2, '2026-10-28 10:00+01', 'completada'),  -- id 1
  (1, 2, 1, 1, '2026-10-29 17:00+01', 'completada'),  -- id 2
  (1, 3, 2, 3, '2026-11-03 11:00+01', 'confirmada'),  -- id 3
  (1, 1, 2, 1, '2026-11-04 10:00+01', 'pendiente'),   -- id 4
  (2, 4, 3, 4, '2026-10-30 12:00+01', 'completada'),  -- id 5
  (2, 5, 4, 5, '2026-11-03 18:00+01', 'pendiente');   -- id 6

INSERT INTO ventas (barberia_id, cita_id, cliente_id, concepto, importe, metodo_pago, fecha) VALUES
  (1, 1,    1,    'Corte + barba',   22.50, 'tarjeta',  '2026-10-28 10:45+01'),
  (1, 2,    2,    'Corte clasico',   15.00, 'bizum',    '2026-10-29 17:30+01'),
  (1, NULL, NULL, 'Cera de peinado',  9.00, 'efectivo', '2026-10-29 18:00+01'),
  (2, 5,    4,    'Corte clasico',   13.00, 'efectivo', '2026-10-30 12:30+01');

COMMIT;
