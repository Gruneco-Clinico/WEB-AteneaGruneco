# Inventario de formularios y subset MVP del Form Builder

## Patrones actuales en el proyecto

| Área | Ubicación | Patrón |
|------|-----------|--------|
| Exámenes clínicos | `apps/home/views/exams_dispatch.py` | `exam_config`: id → plantilla + modelo `*Result` |
| Guardado | `exams_*.py` | `ModelForm` + `update_or_create(visita_examen=...)` |
| Plantillas | `apps/templates/examenes_*` | HTML manual, hidden `visita_id`, `paciente_id`, `examen_id` |
| Catálogo | `Examen.campos` (JSON) | Definición aún no usada como renderer único |
| Visita-examen | `VisitaExamen` | Estado `pendiente` → `en_progreso` → `completado` |

## IDs con dispatch legacy (`realizar_examen`)

Todo examen cuyo `examen_id` esté en `apps/home/exam_legacy.py` → flujo actual (plantilla + modelo tipado).

Cualquier otro `examen_id` con fila `Examen` en BD y `campos` no vacío → **Form Builder** (render genérico + `ExamenSubmission` JSON).

## Tipos de campo soportados (MVP)

| `type` | Widget | Notas |
|--------|--------|--------|
| `text` | input text | |
| `textarea` | textarea | |
| `number` | input number | `min`, `max`, `step` |
| `date` | input date | |
| `time` | input time | HH:MM |
| `email` | input email | |
| `select` | select | `options`: `[{value, label}]` |
| `radio` | radio group | mismo |
| `checkbox` | single checkbox | valor booleano |
| `boolean` | Si/No radios | |
| `multiselect` | checkboxes | lista de valores |
| `section` | encabezado | `label` obligatorio; sin `id` o `id` ignorado en guardado |

## Fase 2 (PDF / Historia Clínica)

| `type` / feature | Descripción |
|------------------|-------------|
| `visible_when` | `{"field": "<id>", "equals": <valor>}` en cualquier nodo |
| `repeater` | `fields` hijos; filas `id__idx__subid` en POST |
| `computed` | `formula`: `imc` (`peso_kg`, `talla_cm` en `depends_on`) |
| `help_text` | Texto ayuda bajo el campo |
| `default` | Valor por defecto |

## Formato de `Examen.campos`

Lista de objetos (nodos). También se acepta `{"fields": [...]}`.

Ejemplo mínimo:

```json
[
  {"type": "section", "label": "Datos"},
  {"id": "motivo", "type": "textarea", "label": "Motivo de consulta", "required": true}
]
```
