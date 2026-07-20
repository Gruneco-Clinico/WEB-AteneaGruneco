# C-15 — Exportación CSV: selección de campos por examen (total vs ítems)

- **Épica:** C — UX / Exportación
- **Tipo:** feature
- **Prioridad:** Alta
- **Componentes:** Exportación de proyecto

## Contexto (reunión)
La exportación actual no exportaba ciertos valores y hoy Daniel terminó exportando **todo** (incluida
la anamnesis completa en JSON), lo que genera un consolidado enorme con muchos campos. Lo que se
necesita:
- Para cada examen, poder **seleccionar qué exportar**: solo el **puntaje total** (si tiene) o los
  **campos/ítems** del examen.
- Mostrar un **desplegable por examen** (similar a la selección de campos de impresión de
  [A-04](A-04-seleccion-y-orden-de-impresion.md)) para elegir qué se exporta.
- El foco real de exportación son los **cuestionarios** (CDR, AQD, escalas…), que son tipo tabla
  (pregunta 1..n + total), no los formularios de texto abierto (anamnesis, examen físico), que casi
  nunca se exportan.

Carlos: la deselección de variables está bien; el problema era que no exportaba ciertos valores y que
no había forma clara de elegir total vs ítems.

## Comportamiento actual
- `exportar_csv_proyecto(request, proyecto_id)` en `apps/home/views/projects.py` (solo superusuario):
  - GET renderiza `home/exportar_proyecto_form.html` con demográficos y exámenes del proyecto.
  - POST arma CSV con `demograficos`, `campos_examen`, `examenes` seleccionados.
- No hay selección **por examen** de "solo total" vs "ítems"; el manejo de campos por examen es
  limitado y algunos valores no se exportan.

## Comportamiento esperado
1. En el formulario de exportación, cada examen seleccionado ofrece un desplegable con sus campos
   disponibles (incluyendo "Puntaje total", "Interpretación" y los ítems).
2. El usuario elige por examen si exporta el total, ítems específicos, o ambos.
3. El CSV exporta correctamente los valores seleccionados (corregir los que hoy no se exportan).

## Referencias técnicas
- Vista: `exportar_csv_proyecto()` en `apps/home/views/projects.py` (~línea 331).
- Plantilla: `apps/templates/home/exportar_proyecto_form.html`.
- Metadatos de campos por examen: `normalize_schema()` en `apps/home/form_builder/schema.py`
  y modelos en `apps/home/models/results_*.py`.

## Dependencias
- Comparte patrón de UI de selección de campos con [A-04](A-04-seleccion-y-orden-de-impresion.md).

## Criterios de aceptación
- [ ] Cada examen tiene un desplegable de campos a exportar (total / ítems).
- [ ] El CSV incluye los valores seleccionados y ya no omite valores válidos.
- [ ] Verificado con un cuestionario tipo tabla (ej.: CDR o AQD) exportando total e ítems por separado.
- [ ] Los formularios de texto abierto no obligan a exportar todo por defecto.
