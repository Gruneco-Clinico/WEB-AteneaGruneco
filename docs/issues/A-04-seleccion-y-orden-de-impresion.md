# A-04 — Selección de exámenes/campos a imprimir y definición del orden

- **Épica:** A — Impresión / PDF
- **Tipo:** feature
- **Prioridad:** Alta
- **Componentes:** PDF, UI de impresión

## Contexto (reunión)
Al descargar el PDF hoy se imprime **todo** y en el orden de creación de los formularios. Se pide:
- Poder **seleccionar qué elementos/exámenes** imprimir (no siempre se le imprime todo al paciente).
- Poder **definir el orden** de impresión (ej.: antecedentes deberían ir antes que las pruebas,
  como en una historia clínica real).

Daniel confirma que hoy no se puede seleccionar, pero "debería ser posible" y "sería muy ganador".

## Comportamiento actual
- `_build_exam_sections(visita)` en `apps/home/services/hc_pdf.py` itera **todos** los exámenes
  `estado="completado"` en el orden por defecto del queryset, sin filtro ni ordenamiento configurable.
- La vista de descarga `generar_pdf_historia_clinica_visita()` (`apps/home/views/pdf.py`) no recibe
  parámetros de selección/orden.

## Comportamiento esperado
1. Pantalla/modal previo a la descarga donde el profesional selecciona qué exámenes incluir.
2. Posibilidad de reordenar los exámenes seleccionados (drag & drop o índices).
3. El PDF respeta selección y orden.
4. (Deseable) Selección a nivel de secciones/campos dentro de cada examen.

## Referencias técnicas
- `_build_exam_sections(visita)` y `render_historia_clinica_html()` en `apps/home/services/hc_pdf.py`
  (aceptar lista de `examen_ids` y orden).
- `generar_pdf_historia_clinica_visita(request, visita_id)` en `apps/home/views/pdf.py`
  (leer selección/orden de `request`).
- UI en el detalle de la visita (plantillas `info_paciente/` / `home/`).

## Criterios de aceptación
- [ ] El usuario puede elegir qué exámenes imprimir antes de generar el PDF.
- [ ] El usuario puede definir el orden de aparición de los exámenes.
- [ ] El PDF generado respeta selección y orden.
- [ ] Si no se selecciona nada, comportamiento por defecto = todos (compatibilidad hacia atrás).
