# A-06 — Encabezados de subsección en la impresión (pares craneales, etc.)

- **Épica:** A — Impresión / PDF
- **Tipo:** bug / enhancement
- **Prioridad:** Media
- **Componentes:** PDF, examen neurológico/físico

## Contexto (reunión)
En el examen neurológico la impresión toma el **nombre del formulario** ("Examen neurológico") y
luego lista todos los campos "en plano", sin respetar las **subdivisiones**: pares craneales
(primer par, segundo par, III/IV/VI, quinto par, séptimo…), sensibilidad básica, sensibilidad
especializada, etc. Debería imprimir cada subsección con su encabezado. En el examen cognitivo sí
diferencia las subsecciones (ej.: "apariencia y actitud"), así que sirve de referencia.

## Comportamiento actual
- El renderizado del examen neurológico (id 9, `ExamenNeurologicoResult`,
  `examenes_general/General_ExamenNeurológico.html`) no agrupa por subsección en la impresión;
  toma el nombre del examen como único encabezado.
- El título del bloque proviene de `section.examen_nombre` en `historia_clinica.html`
  (`_build_exam_sections` en `hc_pdf.py`).

## Comportamiento esperado
1. La impresión del examen neurológico (y físico) debe mostrar los **encabezados de subsección**
   (pares craneales y cada par, sensibilidad básica/especializada, reflejos, etc.).
2. Tomar como referencia el examen cognitivo, que ya separa subsecciones correctamente.

## Referencias técnicas
- Registro: id 9 `ExamenNeurologicoResult`, id 3 `ExamenFisicoResult` (`apps/home/exam_registry.py`).
- Plantillas de resultado: `apps/templates/examenes_resultados/` y las de
  `apps/templates/examenes_general/`.
- Referencia correcta: `examenes_resultados/resultado_cognitivo_Anamnesis.html`.

## Criterios de aceptación
- [ ] La impresión del examen neurológico muestra las subsecciones con sus encabezados.
- [ ] Cada par craneal y grupo de sensibilidad/reflejos aparece bajo su título.
- [ ] Aplicado también al examen físico.

## Relacionado
- Depende parcialmente de [A-05](A-05-impresion-usa-variable-en-vez-de-etiqueta.md) (etiquetas).
- Relacionado con [B-08](B-08-estandarizar-toggles-examen-fisico.md) y [B-09](B-09-boton-evaluado-no-evaluado.md).
