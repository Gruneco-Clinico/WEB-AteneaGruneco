# B-09 — Botón "Evaluado / No evaluado" por sección en examen físico/neurológico

- **Épica:** B — Formularios
- **Tipo:** feature / cumplimiento normativo
- **Prioridad:** Alta
- **Componentes:** Examen físico (id 3), Examen neurológico (id 9)

## Contexto (reunión)
Las historias clínicas ahora exigen marcar si cada sección fue **evaluada o no evaluada**. Solo
aplica a los formularios de **examen físico** y **examen neurológico**, sobre los "ítems gruesos"
(secciones), por ejemplo "pares craneales".

Comportamiento pedido:
- Cada sección tiene un control **Evaluado / No evaluado**.
- **Evaluado** → despliega los campos de la sección.
- **No evaluado** → oculta los campos y en la impresión aparece solo, p. ej., "Pares craneales: no evaluado".

## Comportamiento esperado
1. Agregar control "Evaluado/No evaluado" por sección en examen físico y neurológico.
2. Mostrar/ocultar los campos de la sección según el estado (lógica condicional del formulario).
3. En impresión, si la sección es "no evaluado", imprimir solo el rótulo de la sección con "No evaluado".

## Referencias técnicas
- Plantillas: `apps/templates/examenes_general/General_ExamenFísico.html`,
  `General_ExamenNeurológico.html`.
- Modelos: `ExamenFisicoResult` (id 3), `ExamenNeurologicoResult` (id 9) en
  `apps/home/models/results_general.py` (nuevos campos de estado por sección; requiere migración).
- Impresión: plantillas de resultado en `apps/templates/examenes_resultados/`.

## Dependencias
- Relacionado con [B-08](B-08-estandarizar-toggles-examen-fisico.md) (misma familia de formularios)
  y [A-06](A-06-encabezados-de-subseccion-en-impresion.md) (subsecciones en impresión).

## Criterios de aceptación
- [ ] Cada sección gruesa del examen físico y neurológico tiene control Evaluado/No evaluado.
- [ ] "No evaluado" oculta los campos en el formulario.
- [ ] La impresión refleja "Sección: No evaluado" cuando corresponde.
- [ ] Solo aplica a examen físico y neurológico.
