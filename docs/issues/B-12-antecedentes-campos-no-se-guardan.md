# B-12 — Bug: campos de Antecedentes no se guardan/muestran completos

- **Épica:** B — Formularios
- **Tipo:** bug
- **Prioridad:** Media
- **Componentes:** Antecedentes (id 5)

## Contexto (reunión)
Los antecedentes mejoraron respecto a antes (ya salen más completos en impresión), pero persisten casos:
- Campos que se diligencian y **no salen** en impresión (ej.: "recibido tratamiento", "complicaciones",
  "activo actualmente", "observaciones" de un antecedente patológico).
- **Diagnósticos** (estado: confirmado nuevo / confirmado antiguo / en estudio) que **no quedan
  guardados** al actualizar.
- La impresión refleja exactamente lo que muestra "Ver" (así que el problema real está en cómo se
  guardan/recuperan los datos, no solo en la impresión).

Es parte del trabajo grande de revisar ~40 formularios de antecedentes: cómo se guardan y editan.

## Comportamiento actual
- Antecedentes usa el puente `AntecedentesVisitaLink` → `AntecedentesResult` con múltiples relaciones
  (`get_context_ver_examen()`, id 5, en `apps/home/services/exam_view_context.py`).
- Algunos subcampos no persisten o no se recuperan; el flujo de guardado de diagnósticos no conserva
  el estado.

## Comportamiento esperado
1. Todos los subcampos diligenciados de cada antecedente se guardan y se muestran (ver + impresión).
2. El estado de los diagnósticos (confirmado nuevo/antiguo/en estudio) se persiste correctamente.

## Referencias técnicas
- Modelos: `AntecedentesResult` y relacionados en `apps/home/models/results_general.py`
  (campos `confirmado_nuevo`, `confirmado_antiguo`, etc.).
- Vista de guardado/edición de antecedentes en `apps/home/views/exams_general.py`.
- Plantilla captura: `apps/templates/examenes_general/General_Antecedentes.html`;
  resultado: `apps/templates/examenes_resultados/resultado_antecedentes.html`.

## Dependencias
- Relacionado con [B-11](B-11-editar-formularios-legacy-no-carga-datos.md) (precarga en edición).

## Criterios de aceptación
- [ ] Los subcampos de antecedentes patológicos (tratamiento, complicaciones, activo, observaciones) se guardan y se ven.
- [ ] El estado de diagnósticos se guarda y persiste tras "Actualizar".
- [ ] Impresión y "Ver" muestran los mismos datos completos.
