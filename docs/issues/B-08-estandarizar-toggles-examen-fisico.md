# B-08 — Estandarizar toggles de examen físico/neurológico (normal/anormal, presente/ausente, detecta)

- **Épica:** B — Formularios
- **Tipo:** bug / refactor de datos
- **Prioridad:** Alta
- **Componentes:** Examen físico (id 3), Examen neurológico (id 9)

## Contexto (reunión)
Los toggles/booleanos del examen físico y neurológico son confusos y hoy generan reportes erróneos:
el médico marca "todo bien", pero la impresión sale como "todo alterado". Además los valores en
`false` **no se imprimen** (solo se ven los `true`), y se imprime el nombre de variable con `True`.

Acuerdos de la reunión:
- Por defecto, **todos los toggles inician activos = normal/presente** (el médico va "destildando"
  lo alterado).
- Estandarizar la semántica según el tipo de ítem:
  - **Detecta / No detecta** → solo el par olfatorio (activo = *detecta* = normal).
  - **Presente / Ausente** → síntomas (amaurosis, oscurecimientos, fotopsias, diplopía, síntomas
    auditivos/vestibulares…). No seleccionado = *ausente* (normal); seleccionado = *presente* (hallazgo).
  - **Normal / Anormal** → el resto de estructuras evaluadas (izquierdo/derecho, sensibilidad,
    reflejos, etc.). Cada lado (izquierdo y derecho) debe tener su propio normal/anormal.
- Mostrar al lado del toggle la **etiqueta de interpretación** (p. ej. "Presente"/"Ausente") para que
  la persona sepa qué significa el estado, y que **esa interpretación sea la que se imprime**.
- En impresión: imprimir **también los `false`**, pero con su etiqueta ("Ausente"/"Normal"), no
  omitirlos.

## Comportamiento actual
- Modelos: `ExamenFisicoResult` (id 3), `ExamenNeurologicoResult` (id 9)
  (`apps/home/models/results_general.py`; ver `apps/home/exam_registry.py`).
- La impresión omite valores `false` y muestra `True`/nombre de variable (ligado a
  [A-05](A-05-impresion-usa-variable-en-vez-de-etiqueta.md)).
- El default de los toggles no es "normal/presente".

## Comportamiento esperado
1. Inicializar todos los toggles del examen físico/neurológico en el estado normal por defecto.
2. Aplicar la semántica por ítem (detecta / presente-ausente / normal-anormal) según el mapeo que
   entregará Carlos (lista campo→interpretación).
3. Mostrar la etiqueta de interpretación junto al control en el formulario.
4. En impresión, mostrar el estado interpretado tanto para `true` como para `false`.

## Referencias técnicas
- Plantillas de captura: `apps/templates/examenes_general/General_ExamenFísico.html`,
  `General_ExamenNeurológico.html`.
- Plantillas de resultado/impresión: `apps/templates/examenes_resultados/` correspondientes.
- Modelos: `apps/home/models/results_general.py` (campos booleanos; posible ajuste de `default=True`
  con migración).

## Dependencias / notas
- Carlos entregará el **mapeo campo → interpretación** (cuál es "detecta", cuál "presente/ausente",
  cuál "normal/anormal"). Bloqueante para el detalle fino.
- Al ser formularios legacy, el cambio es por código (no editables desde el builder).
- Posible reunión específica solo para el examen neurológico (acordado en la reunión).

## Criterios de aceptación
- [ ] Todos los toggles inician en estado normal/presente por defecto.
- [ ] Olfatorio usa "detecta/no detecta"; síntomas usan "presente/ausente"; estructuras usan "normal/anormal" (por lado).
- [ ] El formulario muestra la etiqueta de interpretación junto a cada control.
- [ ] La impresión muestra la interpretación correcta para `true` y `false`.
- [ ] Un examen marcado "todo normal" se imprime como "todo normal".
