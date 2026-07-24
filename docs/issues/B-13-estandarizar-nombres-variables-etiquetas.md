# B-13 — Estandarizar nombres de variables y etiquetas en formularios

- **Épica:** B — Formularios
- **Tipo:** tarea / calidad
- **Prioridad:** Baja
- **Componentes:** Formularios (varios), builder

## Contexto (reunión)
Algunos formularios creados por los jóvenes investigadores/semilleristas tienen nombres de variables
"muy creativos" (con caracteres no válidos/incoherentes). Carlos revisará los formularios y los
nombres de variables. Los formularios más recientes que pasó Daniel ya tenían nombres coherentes;
los hechos por Silvia y Carlos también. Esto complementa a [A-05](A-05-impresion-usa-variable-en-vez-de-etiqueta.md):
aunque la impresión debe mostrar la etiqueta, conviene sanear los nombres de variable.

## Comportamiento esperado
1. Revisar los formularios (especialmente los de semilleristas) y normalizar nombres de variables
   (snake_case, sin tildes/espacios/caracteres especiales, ASCII).
2. Asegurar que cada campo tenga una **etiqueta legible** definida (usada en impresión/ver/exportación).

## Referencias técnicas
- Esquema de campos del builder: `apps/home/form_builder/schema.py` (`normalize_schema`).
- Inventario de formularios: `docs/analysis/FORM_BUILDER_INVENTORY.md`.
- Modelos legacy: `apps/home/models/results_*.py` (`verbose_name`).

## Criterios de aceptación
- [ ] Inventario de formularios con nombres de variable no conformes.
- [ ] Nombres de variable normalizados (ASCII, snake_case) sin romper datos existentes.
- [ ] Cada campo tiene etiqueta legible definida.
