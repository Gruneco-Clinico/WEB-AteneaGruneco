# Manual de usuario — Form Builder (exámenes dinámicos)

Este documento explica **cómo usar el constructor visual de exámenes** en Atenea: qué hace cada tipo de campo, cómo se organizan en pantalla y cómo fluye la información desde el diseño hasta el guardado de respuestas.

**Audiencia:** personal que diseña o mantiene plantillas de examen (administración / coordinación clínica).

**Referencia técnica del JSON:** [analysis/FORM_BUILDER_SCHEMA.md](analysis/FORM_BUILDER_SCHEMA.md).

---

## 1. ¿Qué es el Form Builder?

El **Form Builder** permite definir un examen como una **lista ordenada de bloques y campos** (texto, números, listas, secciones, tablas repetibles, valores calculados, etc.). Esa definición se guarda en el examen y, cuando un paciente tiene una visita con ese examen, el sistema **genera el formulario automáticamente** y valida las respuestas al guardar.

```mermaid
flowchart LR
  A[Diseñador crea o edita examen] --> B[Guarda plantilla JSON en Examen.campos]
  B --> C{¿Publicar al guardar?}
  C -->|Sí| D[Se fija versión del esquema]
  C -->|No| E[Solo se guarda borrador]
  D --> F[Visita con ese examen]
  E --> F
  F --> G[Formulario examen_generico]
  G --> H[Validación y respuestas en BD]
```

---

## 2. Pantalla del editor (tres zonas)

Al **editar un examen** del builder verá tres columnas principales y pestañas arriba.

```mermaid
flowchart TB
  subgraph pantalla["Pantalla del editor"]
    direction TB
    tabs["Pestañas: Editor | Vista previa | JSON"]
    subgraph cols["Tres columnas"]
      direction LR
      P["Paleta: botones por tipo de campo"]
      L["Lienzo: tarjetas anidadas y orden"]
      R["Propiedades del elemento seleccionado"]
    end
    tabs --> cols
  end
```

| Zona | Uso |
|------|-----|
| **Paleta** | Añade un **nuevo** bloque o campo del tipo elegido (sección, texto, número, etc.). |
| **Lienzo** | Muestra la **estructura** del formulario. Puede **arrastrar** tarjetas para reordenar. Cada tarjeta tiene acciones (eliminar, duplicar, mover dentro de sección o repetidor). |
| **Propiedades** | Al **seleccionar** una tarjeta en el lienzo, aquí se editan etiqueta, id, obligatoriedad, opciones, condiciones de visibilidad, etc. |

### Pestañas

- **Editor:** diseño habitual (paleta + lienzo + propiedades).
- **Vista previa:** genera una vista de solo lectura del formulario (útil para revisar antes de publicar). Use el botón de actualizar vista previa si está disponible.
- **JSON:** muestra el **contenido exacto** que se guardará (`campos_json`). Avanzado; sirve para copiar o auditar la plantilla.

---

## 3. Flujo de trabajo recomendado

```mermaid
flowchart TD
  Start([Abrir lista de exámenes del builder]) --> Crear{Crear nuevo o editar existente}
  Crear --> Estructura[Definir secciones y campos en el lienzo]
  Estructura --> Ids[Revisar ids únicos y etiquetas claras]
  Ids --> Cond[Opcional: visibilidad condicional]
  Cond --> Rep[Opcional: repetidores y calculados]
  Rep --> Prev[Vista previa]
  Prev --> Ok{¿Correcto?}
  Ok -->|No| Estructura
  Ok -->|Sí| Guardar[Guardar formulario del examen]
  Guardar --> Pub{¿Publicar al guardar?}
  Pub -->|Sí| Listo([Examen listo para usarse en visitas])
  Pub -->|No| Borrador([Cambios guardados; publicar después si aplica])
```

---

## 4. Componentes de la paleta (qué hace cada uno)

Todos los campos con valor (excepto la **sección**) tienen un **`id`**: es la **clave** con la que se guardan los datos. Debe ser **único** en todo el examen y conviene que sea estable (no cambiarlo a la ligera si ya hay datos guardados).

### Sección

- **Qué es:** un **título de bloque** que agrupa otros campos **por debajo** en el árbol.
- **Propiedades:** etiqueta, texto de ayuda opcional, **visibilidad condicional** opcional.
- **Comportamiento:** si la sección está oculta por condición, en el servidor **no se exigen** validaciones de los campos internos de esa sección.

### Texto corto (`text`)

- **Qué es:** una línea de texto o, si activa **entrada multilínea**, un área de texto con varias filas configurables.
- **Propiedades:** id, etiqueta, obligatorio, ayuda, multilínea, filas (altura).

### Texto largo (`textarea`)

- **Qué es:** área de texto amplia (similar a `text` multilínea pero como tipo propio).

### Número

- **Qué es:** valor numérico con controles HTML5.
- **Propiedades:** mínimo, máximo, **paso** (`step`, por ejemplo `0.1` o `1`), obligatorio.

### Fecha / Hora / Correo

- **Fecha:** selector de fecha.
- **Hora:** selector de hora.
- **Correo:** validación de formato de email en el navegador.

### Lista desplegable (`select`)

- **Qué es:** el usuario elige **una** opción de una lista.
- **Propiedades:** **opciones** (cada una con `value` interno y `label` visible). Puede **reordenar** opciones con ↑ / ↓ en el editor.

### Opción única — radio (`radio`)

- **Qué es:** igual que la lista conceptualmente, pero todas las opciones se ven a la vez como botones de radio.

### Casilla (`checkbox`)

- **Qué es:** una sola casilla (sí/no almacenado como valor booleano en datos).

### Sí / No (`boolean`)

- **Qué es:** dos radios explícitos «Sí» y «No».

### Múltiple opción (`multiselect`)

- **Qué es:** varias casillas; la respuesta guardada es una **lista** de valores.
- **Propiedades:** mismas opciones que `select`; reordenables.

### Repetidor

- **Qué es:** una **tabla dinámica**: el usuario puede añadir **filas**; cada fila repite los subcampos definidos dentro del repetidor.
- **Propiedades:** id, etiqueta, obligatorio (al menos una fila), texto del botón **«agregar fila»** (`add_label`), ayuda, subcampos anidados en el lienzo, visibilidad condicional del bloque entero.
- **Nota:** los nombres técnicos en el navegador llevan prefijos `idRepetidor__n__subcampo`. La **visibilidad condicional** que dependa de un campo **solo dentro** de una fila tiene limitaciones; lo más seguro es condicionar respecto a campos **fuera** del repetidor o al mismo nivel.

### Calculado

- **Qué es:** campo **de solo lectura** cuyo valor calcula el **servidor** al guardar (y puede mostrarse en vivo en algunos casos, p. ej. IMC).
- **Propiedades:** fórmula, número de decimales, **dependencias** (qué otros `id` intervienen), ayuda.
- **IMC:** fórmula especial `imc` con dependencias típicamente peso (kg) y talla (cm); el sistema aplica la fórmula clínica habitual.

---

## 5. Visibilidad condicional («Mostrar solo si…»)

Permite **mostrar u ocultar** un bloque (sección, repetidor o campo) según el valor de **otro campo que aparece antes** en el formulario (orden en el lienzo).

```mermaid
flowchart LR
  A[Campo dependiente A] --> B{¿Condición sobre A?}
  B -->|Sí| C[Mostrar bloque B]
  B -->|No| D[Ocultar bloque B]
```

| Condición en la interfaz | Significado breve |
|--------------------------|-------------------|
| **Igual a** | El valor actual debe coincidir con el esperado. |
| **Distinto de** | Debe ser diferente al esperado. |
| **Contiene** | Para texto, si el texto incluye el fragmento; para multiselect, si la lista incluye el **value** de la opción elegida. |

El editor adapta el control de **valor esperado** al tipo del campo dependiente (lista, número, sí/no, texto).

---

## 6. Orden, duplicado y validaciones del editor

- **Arrastrar** tarjetas en el lienzo reordena el formulario (incluido dentro de secciones y repetidores, según la jerarquía).
- **Duplicar** crea una copia; el sistema suele **sufijar el id** para evitar colisiones — revíselo en propiedades.
- Al **guardar** el examen, el cliente puede avisar si faltan **ids**, hay **ids duplicados**, opciones vacías en listas, o un calculado sin fórmula o sin dependencias.

---

## 7. Guardar examen y publicación

- El formulario de edición del examen envía la definición en **`campos_json`**.
- Si marca **«Publicar al guardar»** (u opción equivalente en su pantalla), el sistema **fija una versión del esquema** alineada con ese JSON, lo cual ayuda a trazabilidad cuando las respuestas se asocian a una versión concreta de la plantilla.
- Si no publica, los cambios pueden quedar como **borrador** según la política del sistema; consulte con su administrador cuándo es obligatorio publicar.

---

## 8. Experiencia del usuario en la visita (rellenar el examen)

```mermaid
sequenceDiagram
  participant U as Usuario clínico
  participant V as Vista examen_generico
  participant S as Servidor Django

  U->>V: Abre examen de la visita
  V->>U: Muestra campos según plantilla
  U->>V: Cambia valores / añade filas repetidor
  V->>V: Actualiza visibilidad condicional en el navegador
  U->>S: Enviar Guardar
  S->>S: Validar obligatorios, rangos, secciones visibles
  S->>S: Calcular campos computed
  S->>U: Confirmación o mensajes de error
```

- Los campos obligatorios muestran **asterisco** en la etiqueta.
- El botón **Guardar** envía todo el formulario; los errores de validación los muestra el servidor (y el navegador en campos HTML5 como `required`).

---

## 9. Resumen rápido por tipo

| Componente | Dato que guarda | Ocasión de uso típica |
|------------|-----------------|------------------------|
| Sección | (no tiene valor propio) | Agrupar temas |
| Texto / Textarea | Texto | Observaciones, notas |
| Número | Número | Peso, talla, escalas |
| Fecha / Hora / Email | Valor tipado | Epidemiología, citas, contacto |
| Select / Radio | Un `value` | Opciones cerradas |
| Checkbox / Boolean | Booleano | Preguntas sí/no simples |
| Multiselect | Lista de `value` | Síntomas múltiples |
| Repetidor | Lista de filas (objetos) | Medicamentos, familiares, ítems |
| Calculado | Número (u otro según fórmula) | IMC, índices derivados |

---

## 10. Dónde encontrar las pantallas en la aplicación

Las rutas internas de Django suelen incluir (nombres `name` en `urls.py`):

- `exam_builder_list` — listado de exámenes del builder  
- `exam_builder_create` — crear examen nuevo  
- `exam_builder_edit` — editor visual descrito en este manual  

La URL exacta depende del prefijo montado en su instalación (`/.../`). Si no la conoce, pídala al administrador o búsquela en el menú de administración de exámenes / visitas.

---

*Última actualización alineada con el editor en paleta + lienzo + propiedades, SortableJS, vista previa, publicación al guardar y plantilla `field_fragment.html`.*
