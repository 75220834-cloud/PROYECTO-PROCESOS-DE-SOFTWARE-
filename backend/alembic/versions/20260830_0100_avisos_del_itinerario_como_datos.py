"""Los avisos del itinerario pasan de texto concatenado a JSONB.

Hasta la Fase 7 los avisos se guardaban como un solo texto con los avisos
separados por saltos de línea, ya redactados en español. Eso tenía dos
consecuencias:

- **No se podían traducir.** Un visitante en inglés veía la interfaz en inglés
  y estos avisos en español.
- **No se podían consultar.** Saber cuántos itinerarios avisaron de altitud
  exigía buscar subcadenas, que es frágil: basta cambiar una coma.

Ahora se guardan como una lista de ``{"codigo": ..., "parametros": {...}}``.
La frase la pone la interfaz, en el idioma del visitante.

## Sobre los datos existentes

**Los avisos que ya estaban guardados se pierden.** No es descuido: de una
frase en español no se puede deducir qué código la produjo, y adivinarlo
metería datos falsos en la base. Se dejan como lista vacía.

El coste real es nulo: al abrir un itinerario guardado, los avisos se
recalculan a partir de sus paradas. Lo que se pierde es la copia guardada de
una frase que se vuelve a generar sola.

Identificador: 4b1c9d2ea375
Revisa: 9e5f48ead726
Fecha: 30 de agosto de 2026
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "4b1c9d2ea375"
down_revision = "9e5f48ead726"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Texto concatenado -> JSONB, empezando de cero."""
    # Se borra el contenido antes de cambiar el tipo. PostgreSQL no sabe
    # convertir un texto suelto en JSON válido, así que sin esto el ALTER
    # fallaría con «invalid input syntax for type json» en cuanto hubiera una
    # sola fila con avisos.
    op.execute("UPDATE itinerario SET avisos = NULL")

    op.alter_column(
        "itinerario",
        "avisos",
        existing_type=sa.Text(),
        type_=postgresql.JSONB(),
        existing_nullable=True,
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
        postgresql_using="'[]'::jsonb",
    )


def downgrade() -> None:
    """JSONB -> texto, también empezando de cero.

    La vuelta atrás tampoco conserva nada, por el mismo motivo al revés: los
    códigos no traen la frase, así que no hay texto que reconstruir sin repetir
    aquí las traducciones, que viven en el frontend.
    """
    op.alter_column(
        "itinerario",
        "avisos",
        existing_type=postgresql.JSONB(),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=True,
        server_default=None,
        postgresql_using="NULL",
    )
