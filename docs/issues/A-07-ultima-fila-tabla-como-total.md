# A-07 — Última fila de tablas impresa como "total" por error

- **Épica:** A — Impresión / PDF
- **Tipo:** bug
- **Prioridad:** Media
- **Componentes:** PDF, tablas (medicamentos/antecedentes)

## Contexto (reunión)
En tablas que tienen ítems (ej.: **medicamentos** en antecedentes), la impresión resalta **la última
fila como si fuera un total** (en negrita), cuando en realidad es un ítem más. Solo debería
resaltarse como total cuando efectivamente es un total.

## Comportamiento actual
- Alguna plantilla/estilo de tabla del PDF aplica estilo de "total" (negrita) a la última fila de
  forma incondicional. Candidatos:
  - `apps/templates/pdf/examenes/medicamentos_print.html`
  - `apps/templates/examenes_resultados/resultado_medicamentos.html`
  - Reglas en `apps/static/pdf/print.css` del tipo `tr:last-child` con `font-weight:bold`.
- En el fallback ReportLab, `puntaje_total` sí se separa explícitamente
  (`_extract_exam_data` en `apps/home/views/pdf.py`), pero WeasyPrint depende de las plantillas/CSS.

## Comportamiento esperado
1. La última fila de una tabla de ítems **no** debe estilizarse como total.
2. Solo se resalta como total una fila marcada explícitamente como total (o el `puntaje_total`).

## Referencias técnicas
- Revisar selector `:last-child` en `apps/static/pdf/print.css`.
- Plantillas de medicamentos/antecedentes listadas arriba.

## Criterios de aceptación
- [ ] En la tabla de medicamentos, el último medicamento se muestra como fila normal.
- [ ] Solo las filas de total real se muestran en negrita/resaltadas.
- [ ] Verificado en antecedentes con ≥ 2 medicamentos.
