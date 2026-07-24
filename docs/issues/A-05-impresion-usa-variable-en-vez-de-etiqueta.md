# A-05 — Impresión muestra el nombre de la variable en vez de la etiqueta

- **Épica:** A — Impresión / PDF
- **Tipo:** bug
- **Prioridad:** Alta
- **Componentes:** PDF, plantillas de resultados

## Contexto (reunión)
En varios formularios (CDR, examen físico/neurológico, etc.) la impresión muestra el **nombre del
parámetro/variable** en lugar de la **etiqueta/leyenda** legible. Ejemplos citados:
`memoria_1`, `juicio_1`, `ensayo_2`, `deprimido_2`, en vez del texto de la pregunta.
Carlos lo resume: *"está tomando el nombre del campo, no la etiqueta"*. Esta es la corrección
general más repetida.

## Comportamiento actual
- En la ruta genérica, el diccionario `datos_resultado` se arma con `field.verbose_name or field.name`
  en `get_context_ver_examen()` (`apps/home/services/exam_view_context.py`, ~línea 209-213). Cuando el
  modelo no tiene `verbose_name`, cae al `field.name` técnico.
- Para exámenes tipo builder/submission, se usa `submission.answers` cuyas **claves son los nombres
  de parámetro**, no etiquetas (`_render_examen_ver_html()` en `hc_pdf.py`;
  `examenes_builder/resultado_builder.html`).
- La plantilla `apps/templates/examenes_resultados/resultado_generico.html` imprime `campo|capfirst`
  tal cual venga la clave.

## Comportamiento esperado
1. La impresión (y la vista "Ver") deben mostrar **siempre la etiqueta/leyenda** definida para cada
   campo, no el nombre técnico de la variable.
2. Para formularios del builder, mapear cada `answer` a su `label` desde el esquema del examen
   (`normalize_schema(visita_examen.examen.campos)`).
3. Para modelos con campos sin `verbose_name`, agregar `verbose_name` legible.

## Referencias técnicas
- `get_context_ver_examen()` en `apps/home/services/exam_view_context.py`.
- `normalize_schema()` en `apps/home/form_builder/schema.py` (contiene labels de cada campo).
- Plantillas: `examenes_resultados/resultado_generico.html`, `examenes_builder/resultado_builder.html`.

## Criterios de aceptación
- [ ] En impresión y en "Ver" se muestra la etiqueta legible, no `campo_1`/`memoria_2`, etc.
- [ ] Verificado en CDR (cuidador/participante), examen neurológico y un examen builder.
- [ ] No se rompe la visualización de exámenes que ya mostraban etiquetas correctas.
