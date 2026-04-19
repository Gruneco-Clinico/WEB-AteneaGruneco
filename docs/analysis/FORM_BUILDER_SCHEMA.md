# Lenguaje de esquema (Form Builder)

`Examen.campos` es una **lista de nodos** (o `{"fields": [...]}`).

## Nodos soportados

### `section`
```json
{"type": "section", "label": "Título de bloque"}
```

### Campos con valor

| type | Opciones extra |
|------|----------------|
| `text` | `required`, `help_text` |
| `textarea` | igual |
| `number` | `min`, `max`, `required` |
| `date`, `time`, `email` | `required` |
| `select`, `radio` | `options`: `[{"value":"a","label":"A"}]` |
| `checkbox` | un booleano (una casilla) |
| `boolean` | Sí/No (radios) |
| `multiselect` | `options`, mismo formato; valor = lista |

### Condicional
```json
{
  "id": "detalle",
  "type": "text",
  "label": "Detalle",
  "visible_when": {"field": "tiene_dolor", "equals": true}
}
```

### Repetidor
```json
{
  "id": "medicamentos",
  "type": "repeater",
  "label": "Medicamentos",
  "required": false,
  "fields": [
    {"id": "nombre", "type": "text", "label": "Nombre", "required": true},
    {"id": "dosis", "type": "text", "label": "Dosis"}
  ]
}
```

### Calculado (IMC)
```json
{"id": "peso_kg", "type": "number", "label": "Peso (kg)", "required": true},
{"id": "talla_cm", "type": "number", "label": "Talla (cm)", "required": true},
{
  "id": "imc",
  "type": "computed",
  "label": "IMC",
  "formula": "imc",
  "depends_on": ["peso_kg", "talla_cm"],
  "help_text": "peso / (talla en m)²"
}
```

El servidor recalcula IMC al guardar; la vista previa en cliente es opcional (JS en `examen_generico.html`).

## Versionado

Al guardar respuestas se asocia la última `ExamenSchemaVersion` coherente con `Examen.campos`, o se crea una versión nueva si el JSON cambió. Use **Publicar** en el admin del builder para fijar versión explícitamente.
