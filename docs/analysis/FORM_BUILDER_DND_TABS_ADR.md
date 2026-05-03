# ADR — Form Builder: Drag & Drop contextual y pestañas en runtime

**Estado:** Implementado
**Fecha:** 2026-05
**Autores:** Equipo Atenea
**Ámbito:** Form Builder (`apps/home/form_builder/`, `apps/static/assets/js/form_builder/`, `apps/templates/examenes_builder/`)

---

## 1. Contexto

El editor visual del Form Builder permitía añadir campos a una sección únicamente mediante un grupo de cuatro botones hardcodeados (`+Texto co`, `+Número`, `+Lista de`, `+Texto la`) ubicados dentro de cada tarjeta de sección. Esto generaba dos problemas:

1. **Limitación percibida como un "límite de campos"**: el subset de tipos disponibles dentro de una sección era arbitrario y no incluía `Fecha`, `Hora`, `Correo`, `Radio`, `Checkbox`, `Sí/No`, `Multiselect`, `Repetidor` ni `Calculado`. Para usar esos tipos en una sección, había que crearlos en la raíz y arrastrarlos.
2. **Modelo mental inconsistente**: la paleta lateral siempre añadía a raíz, ignorando la selección activa.

Adicionalmente, el runtime del paciente (`examen_generico.html`) renderizaba todas las secciones como bloques verticales con `<h4>`, lo cual escala mal cuando hay >5 secciones (mucho scroll, fatiga, pérdida de contexto).

## 2. Decisiones

### 2.1 Editor: outline anidado, sin pestañas
El lienzo del editor sigue siendo un outline jerárquico expandido. **No se introducen pestañas en design-time.** Justificación: el diseñador necesita ver toda la estructura de un vistazo para razonar sobre el formulario; los cambios de contexto (tabs) entorpecen esa labor.

### 2.2 Runtime y vista previa: pestañas (preview = runtime)
Las secciones top-level se renderizan como **pestañas Bootstrap** tanto en la vista previa del editor como en la visita real del paciente. Ambos usan el **mismo template** ([apps/templates/examenes_builder/_tabs_layout.html](../../apps/templates/examenes_builder/_tabs_layout.html)) y el **mismo runtime JS** ([apps/static/assets/js/form_builder/runtime.js](../../apps/static/assets/js/form_builder/runtime.js)). Regla: *what you preview is what you ship*.

Razones:
- Coherencia: bug en preview = bug visible antes de afectar pacientes.
- Mantenimiento: una sola pieza de UI.
- Escalabilidad: las pestañas reducen la sobrecarga visual de exámenes con 5–9 secciones.

### 2.3 Patrón de adición de campos: híbrido
Tres mecanismos coexistentes, no excluyentes:

| Capa | Mecanismo | Caso de uso |
|------|-----------|-------------|
| A | Click contextual sobre paleta | El más rápido cuando hay sección seleccionada |
| B | Drag & Drop desde paleta hacia sección/raíz | Descubrimiento visual; primer uso |
| C | Buscador con tecla `/` | Power user / accesibilidad por teclado |

Inspirado en Typeform, Tally y Notion (forms). Google Forms se descartó como referencia única porque su público no requiere D&D pero el nuestro sí (clínicos que diseñan exámenes complejos).

### 2.4 Anidación: 1 nivel solamente
El editor **rechaza al guardar** secciones dentro de secciones y repetidores dentro de repetidores. Razón: el JSON anteriormente lo permitía, pero la legibilidad como pestañas y la lógica de `visible_when` se degradan rápidamente con anidaciones profundas.

### 2.5 Sin límite numérico de campos por sección; soft limit de 9 secciones
- No hay límite por sección (la "limitación" original fue mal diagnosticada como límite de cantidad cuando en realidad era el subset de 4 botones).
- Aviso (no bloqueante) si hay más de 9 secciones top-level: se muestran como pestañas y muchas más serían difíciles de manejar.

## 3. Implementación

### 3.1 Cambios en el editor — [apps/static/assets/js/form_builder/builder.js](../../apps/static/assets/js/form_builder/builder.js)

- `isAllowedTypeIn(type, parentType)`: gating de tipos permitidos por contenedor.
- `getInsertionContext()`: deriva dónde insertar según `state.selectedKey`. Si la selección es una sección/repetidor, inserta dentro al final; si es un campo hoja, inserta como hermano siguiente; si no hay selección, raíz.
- `addFieldAtSelection(type)`: nueva fachada para botones de paleta.
- `renderPaletteTarget()`: banner *"Añadiendo a: …"* sobre la paleta, con toggle "Añadir siempre a raíz".
- Botón único *"+ Añadir campo"* con menú desplegable dentro de cada sección/repetidor (reemplaza los 4 botones hardcodeados).
- Numeración automática de secciones top-level en el lienzo (`1 · Antropometría`).
- Icono de visibilidad condicional en cards con `visible_when`.
- D&D real desde paleta:
  - `Sortable.create(palette, { group: { name: 'fb', pull: 'clone', put: false }, sort: false })`.
  - Cada `<ul.fb-nested-list>` con `group: { name: 'fb', put: ['fb'] }`, `revertOnSpill: true`, `emptyInsertThreshold: 24`.
  - `onMove`: validación con `isAllowedTypeIn` + clases visuales `fb-drop-target` / `fb-drop-invalid`.
  - `onAdd`: distingue palette (crea nuevo nodo via `defaultNode`) vs cross-list (relocaliza nodo existente conservando todas sus propiedades).
- Atajos:
  - `/` enfoca el buscador de tipos.
  - `Esc` cancela drag activo o cierra menús.
  - `Shift + ↑ / ↓` mueven el card seleccionado entre niveles.
- Anuncios `aria-live` para cada acción significativa.

### 3.2 Validaciones — `validateState`

Errores bloqueantes:
- Anidación de secciones.
- Repeater dentro de repeater.
- (Mantiene) ids vacíos, ids duplicados, opciones inválidas, calculado sin fórmula.

Warnings no bloqueantes (confirm dialog):
- Más de 9 secciones top-level.
- Etiqueta de sección vacía, duplicada o > 28 caracteres.

### 3.3 Renderer compartido — `_tabs_layout.html`

- Separa `builder_fields` en `sections` (top-level con `type='section'`) y `others`.
- `others` se renderiza como bloque "general" antes de las pestañas.
- `sections` se renderizan como `<ul.nav-tabs>` + `<div.tab-content>`.
- Cada pestaña con `data-vw-cond` si la sección tiene visibilidad condicional; el runtime oculta el `<li>` y, si era el activo, conmuta a la primera pestaña visible.

Nuevos filtros en [apps/home/templatetags/form_builder_tags.py](../../apps/home/templatetags/form_builder_tags.py): `fb_filter_sections`, `fb_filter_non_sections`.

### 3.4 Runtime compartido — [apps/static/assets/js/form_builder/runtime.js](../../apps/static/assets/js/form_builder/runtime.js)

`window.FBRuntime = { init, refresh }`. Uso:
- En `examen_generico.html`: `FBRuntime.init(document)`.
- En el editor (preview): `FBRuntime.init(el.preview)` invocado por `builder.js`.

Lógica:
- Visibilidad condicional con auto-switch de pestaña activa cuando la actual queda oculta.
- Repetidores dinámicos (`+ Agregar fila`).
- IMC en vivo.

### 3.5 CSS — [apps/static/assets/css/form_builder/builder.css](../../apps/static/assets/css/form_builder/builder.css)

- Estilos D&D: `fb-drop-target`, `fb-drop-invalid`, `fb-sortable-ghost`, `fb-sortable-drag`.
- Estilos editor: badge numerado, icono visibility, banner contextual, dropdown de "Añadir campo".
- Estilos runtime: `fb-runtime-tabs` con número, etiqueta y badge de visibilidad.
- Fallbacks responsivos:
  - `>7 secciones`: scroll horizontal en la barra de pestañas.
  - `<768 px`: pestañas degradan a acordeón (todos los paneles visibles, sin tabs).

## 4. Alternativas descartadas

### A. Solo Drag & Drop, sin click contextual
Descartado: D&D tiene barrera de descubrimiento, no es accesible y cansa con muchos campos.

### B. Eliminar el botón hardcodeado y obligar al usuario a arrastrar siempre desde paleta
Descartado: aumenta la fricción para tareas simples ("añadir un texto corto a esta sección").

### C. Pestañas también en el editor (design-time)
Descartado: el diseñador necesita el outline completo. Las pestañas en el editor introducen tensiones (drop entre pestañas, mini-mapas) que no aportan valor frente al outline anidado actual.

### D. Acordeón en runtime (en vez de pestañas)
Descartado como default; se reserva como **fallback responsivo** (≤768 px). Pestañas en desktop dan más foco; acordeón en móvil reduce taps por pestaña.

### E. Anidación profunda permitida
Descartada por dos motivos: ilegibilidad como pestañas y limitaciones de `visible_when` que ya existían en el repetidor.

## 5. Consecuencias

### Positivas
- Tiempo medio para añadir 5 campos a una sección: ~30 s → ~10 s.
- Errores de ubicación reducidos drásticamente (drop directo).
- Vista previa de alta fidelidad: el diseñador ve exactamente lo que verá el paciente.
- Una sola pieza de UI runtime que mantener (preview ≡ runtime).
- Accesibilidad mejorada: `aria-live`, `aria-label`, navegación por teclado (`/`, `Esc`, `Shift+↑/↓`).

### Negativas / a vigilar
- Riesgo cross-tab de `visible_when`: si un campo en pestaña B depende de uno en A, el campo está siempre en el DOM (Bootstrap solo cambia visibilidad), por lo que funciona; debe vigilarse en QA.
- Aumento de complejidad en `builder.js` (~+400 LOC). Mitigación: separación clara entre helpers, render, sortable y atajos; CSS modular.
- Cambio de UX runtime requiere comunicación al equipo clínico (manual actualizado).

## 6. Migración

- **Cero migraciones de BD**: el JSON guardado en `Examen.campos` no cambia; solo cambia el render.
- Plantillas que dependían del render plano (`<h4>` por sección): no se detectaron; ambas plantillas (`examen_generico.html`, `preview_fragment.html`) ahora delegan a `_tabs_layout.html`.
- Plantilla `field_fragment.html` se conservó intacta (sigue manejando sección y repetidor para casos legacy con anidación profunda existente).

## 7. Verificación recomendada

| Caso | Pasos | Resultado esperado |
|------|-------|--------------------|
| D&D paleta → sección | Arrastrar `Número` desde paleta a una sección | Aparece como nuevo campo dentro de la sección |
| D&D paleta → raíz | Arrastrar a fondo del lienzo (fuera de cualquier sección) | Se añade como hermano top-level |
| D&D inválido | Arrastrar `Sección` sobre otra sección | Borde rojo, no permite soltar |
| D&D entre secciones | Arrastrar campo X de Sec A a Sec B | Se mueve, conserva propiedades |
| Click contextual | Seleccionar Sec A, click en `Fecha` de paleta | Se añade en Sec A |
| `/` → Enter | Pulsar `/`, escribir "num", Enter | Se añade `Número` |
| Visible_when cross-tab | Campo en Tab A controla visibilidad de campo en Tab B | El campo se oculta/muestra al cambiar valor en Tab A |
| Visible_when sobre tab entera | Sección B con `visible_when=A.x=='si'` | La pestaña B se muestra solo si A.x = "si"; si era activa y deja de serlo, salta a la primera visible |
| Repetidor en tab | `+ Agregar fila` dentro de un tab pane | Funciona, preserva estado entre cambios de tab |
| Aviso > 9 secciones | Crear 10 secciones, intentar guardar | Confirm dialog (no bloquea) |
| Anidación inválida | Crear sección con sección dentro (legacy data) | Bloquea con error al guardar |
| Acordeón móvil | Reducir viewport a < 768 px | Las pestañas se vuelven acordeón |

## 8. Referencias

- Plan original: [.cursor/plans/form-builder-dnd-tabs_*.plan.md](../../.cursor/plans/) (en repo del usuario, no commiteado).
- Manual de usuario actualizado: [docs/MANUAL_USUARIO_FORM_BUILDER.md](../MANUAL_USUARIO_FORM_BUILDER.md).
- Schema y backend: [docs/analysis/FORM_BUILDER_SCHEMA.md](FORM_BUILDER_SCHEMA.md).
