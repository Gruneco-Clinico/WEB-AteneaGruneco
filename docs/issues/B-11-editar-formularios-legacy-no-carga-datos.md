# B-11 — Bug: al editar formularios legacy no cargan los datos guardados

- **Épica:** B — Formularios
- **Tipo:** bug
- **Prioridad:** Alta
- **Componentes:** Edición de exámenes (legacy)

## Contexto (reunión)
Al entrar a **editar** ciertos formularios ya diligenciados, el formulario aparece **en blanco**: no
carga los datos guardados. "Ver" sí muestra la información, pero "Editar" no la precarga. Se confirmó
que ocurre **tanto en testing como en producción**. Daniel: "no carga los datos, pero creo que esa no
es tan difícil de solucionar".

## Comportamiento actual
- La vista "Ver" recupera y muestra los datos (`get_context_ver_examen()` en
  `apps/home/services/exam_view_context.py`).
- La vista "Editar" no está precargando los valores en los formularios legacy (los campos salen vacíos).
- Rutas de edición en `apps/home/views/exams_dispatch.py` / `exams_general.py` y plantillas de
  `apps/templates/examenes_general/`.

## Comportamiento esperado
1. Al editar un examen ya guardado, el formulario debe precargar todos los valores existentes.
2. Debe funcionar en los formularios "grandes" legacy (examen físico, neurológico, antecedentes,
   análisis general, etc.).

## Referencias técnicas
- Vistas de edición: `apps/home/views/exams_dispatch.py`, `apps/home/views/exams_general.py`.
- Comparar con el armado de contexto de "Ver" que sí funciona
  (`apps/home/services/exam_view_context.py`).
- `EXAM_REGISTRY` en `apps/home/exam_registry.py` (modelos y `related_name`).

## Notas
- Descartar que sea solo un problema de datos migrados en *testing*: se reprodujo también en producción.

## Criterios de aceptación
- [ ] Al editar un examen guardado, todos los campos aparecen precargados con sus valores.
- [ ] Reproducido y corregido en examen físico, neurológico y antecedentes.
- [ ] Verificado en producción (o entorno equivalente con datos reales).
