"""Mide la similitud de preguntas de prueba para elegir el umbral del "no lo se"."""
from cargar import conectar, como_vector, embeddings

BARBERIA_ID = 1  # El Navajas

# (pregunta, deberia encontrar respuesta en los documentos?)
PREGUNTAS = [
    ("¿Puedo anular mi reserva el mismo día?", True),
    ("¿A qué hora abrís los sábados?", True),
    ("¿Se puede pagar con Bizum?", True),
    ("¿Qué hago si se me irrita la piel después de afeitarme?", True),
    ("¿Cada cuánto tengo que volver para repasar el degradado?", True),
    ("¿Qué pasa si llego tarde a la cita?", True),
    ("¿Hacéis tatuajes?", False),
    ("¿Tenéis parking?", False),
    ("¿Cuánto cuesta un corte de pelo?", False),
    ("¿Vendéis productos para el pelo?", False),
    ("¿Quién ganó el partido del Athletic?", False),
]


def main():
    vectores = embeddings([p for p, _ in PREGUNTAS])
    with conectar() as conn, conn.cursor() as cur:
        print(f"{'¿Debería?':<10} {'Similitud':<10} {'Mejor fragmento':<45} Pregunta")
        print("-" * 120)
        for (pregunta, deberia), vector in zip(PREGUNTAS, vectores):
            v = como_vector(vector)
            cur.execute("""
                SELECT 1 - (c.embedding <=> %s::vector), d.fuente || ' > ' || c.seccion
                FROM documento_chunks c
                JOIN documentos d ON d.id = c.documento_id
                WHERE c.barberia_id = %s
                ORDER BY c.embedding <=> %s::vector
                LIMIT 1
            """, (v, BARBERIA_ID, v))
            similitud, fragmento = cur.fetchone()
            print(f"{'SÍ' if deberia else 'NO':<10} {similitud:<10.3f} {fragmento:<45} {pregunta}")


if __name__ == "__main__":
    main()
