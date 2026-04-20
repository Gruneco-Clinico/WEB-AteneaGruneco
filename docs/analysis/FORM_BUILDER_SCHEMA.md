# Lenguaje de esquema (Form Builder)

`Examen.campos` es una **lista de nodos** (o `{"fields": [...]}`). Cada nodo es un objeto; el servidor valida y parsea el POST con `apps/home/form_builder/schema.py`. La UI del examen usa `field_fragment.html` y el JS de `examen_generico.html` (visibilidad y repetidores).

## Nodos de agrupación

### `section`

Bloque visual con título. Puede contener `fields` (árbol anidado).

| Propiedad | Descripción |
|-----------|-------------|
| `type` | `"section"` |
| `label` | Título (obligatorio en la práctica) |
| `help_text` | Texto opcional bajo el título |
| `fields` | Lista de nodos hijos |
| `visible_when` | Igual que en campos simples: si la condición es falsa, **toda la sección** se oculta en el cliente y **no se validan** los hijos en el servidor |

```json
{
  "type": "section",
  "label": "Antecedentes",
  "help_text": "Complete solo si aplica.",
  "visible_when": { "field": "tiene_antecedentes", "op": "equals", "equals": true },
  "fields": []
}
```

### `repeater`

Lista de filas; cada fila es un diccionario de respuestas para los `fields` internos. Los nombres en el POST son `repeaterId__índice__subcampoId`.

| Propiedad | Descripción |
|-----------|-------------|
| `id`, `label` | Identificador y etiqueta |
| `required` | Si es obligatorio, debe haber al menos una fila |
| `help_text` | Ayuda bajo la etiqueta |
| `add_label` | Texto del botón para añadir fila (por defecto en plantilla: «+ Agregar fila») |
| `fields` | Definición de columnas (mismos tipos que un campo simple, sin anidar otro `repeater` en la misma fila salvo que el runtime lo permita) |
| `visible_when` | Condición sobre el diccionario global de respuestas (no sobre una celda concreta) |

## Campos con valor (hojas)

| type | Notas |
|------|--------|
| `text` | `required`, `help_text`. Opcional: `multiline` (bool) y `rows` (entero) para renderizar `<textarea>` en lugar de `<input type="text">`. |
| `textarea` | Texto largo; `rows` puede usarse en plantilla (por defecto 3). |
| `number` | `min`, `max`, `step` (opcional, string o número para HTML `step`), `required`. |
| `date`, `time`, `email` | `required`, `help_text`. |
| `select`, `radio` | `options`: `[{"value":"a","label":"A"}]`. `required`. |
| `checkbox` | Una casilla; valor booleano. |
| `boolean` | Radios Sí/No; valor booleano. |
| `multiselect` | `options`; valor = lista de strings en respuestas. |

## `visible_when` (condicional)

Objeto opcional en **cualquier** nodo que se renderice como bloque (sección, repetidor, campo).

| Clave | Descripción |
|-------|-------------|
| `field` | `id` del campo del que depende la visibilidad |
| `op` | `"equals"` (defecto), `"not_equals"`, `"contains"` |
| `equals` o `value` | Valor esperado (el servidor acepta ambas claves; el editor usa `equals`). Para booleanos conviene usar JSON `true`/`false`, no solo strings. |

En el cliente, la condición va en `data-vw-cond` (JSON escapado). El operador `contains` para multiselect comprueba si el valor está en la lista seleccionada.

**Limitación:** un `field` que vive **solo** dentro de un repetidor tiene nombres de control con prefijo `id__n__`; la visibilidad condicional referenciando ese `id` desde fuera del repetidor puede no coincidir con un único control en el DOM. Use condiciones entre campos del mismo ámbito (p. ej. dos campos al mismo nivel).

## `computed`

Campo de solo lectura calculado al guardar.

| Clave | Descripción |
|-------|-------------|
| `id`, `label` | Identificador y etiqueta |
| `formula` | Expresión aritmética o la palabra clave `imc` |
| `depends_on` | Lista de `id` numéricos usados en la fórmula |
| `precision` | Decimales al redondear (opcional) |
| `help_text` | Texto de ayuda bajo el control |

Para `formula: "imc"` se usan típicamente `depends_on: ["peso_kg", "talla_cm"]` (talla en cm). El servidor recalcula al validar el POST; el JS en `examen_generico.html` puede actualizar una vista en vivo para IMC.

## Versionado

Al guardar respuestas se asocia la última `ExamenSchemaVersion` coherente con `Examen.campos`, o se crea una versión nueva si el JSON cambió. Use **Publicar** en el admin del builder para fijar versión explícitamente.
