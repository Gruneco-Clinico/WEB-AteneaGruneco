# Testing del Form Builder

Batería completa de tests para el módulo de exámenes dinámicos
(`apps/home/form_builder/` y `apps/static/assets/js/form_builder/`).

## Resumen

| Capa     | Tests | Framework                          | Tiempo     |
| -------- | ----- | ---------------------------------- | ---------- |
| Backend  | 126   | `django.test` (`SimpleTestCase` / `TestCase`) | ~2.3 s     |
| Frontend | 28    | Vitest + jsdom                     | < 1 s      |
| **Paridad backend ↔ frontend** | 10 casos compartidos | tabla JSON común | n/a |

## Archivos creados

### Backend

```
apps/home/tests/
  test_form_builder_schema.py        # 64 tests: normalize, visible_when,
                                     #   parse_post, validate_leaf, computed
  test_form_builder_security.py      # 21 tests: sandbox de fórmulas (inyección)
  test_form_builder_views.py         # 20 tests: vistas, ensure_schema_version,
                                     #   guardar_examen_builder, constraints
  test_form_builder_templatetags.py  # 20 tests: filtros y simple_tags
  test_form_builder_parity.py        # 1 test (10 subTests): paridad con JS
```

### Frontend

```
tests/js/
  runtime.spec.js   # 28 tests: visibilidad, IMC, tabs, repeaters, API
  parity.spec.js    # 10 tests: misma tabla que test_form_builder_parity.py
tests/fixtures/
  visible_when_cases.json   # tabla compartida backend ↔ frontend
```

### Configuración

```
core/test_settings.py    # SQLite en memoria (no requiere mysqlclient)
package.json             # scripts test/test:watch + devDeps vitest, jsdom
vitest.config.js         # entorno jsdom, include tests/js/**/*.spec.js
```

## Cómo ejecutar

### Backend

```bash
source venv/bin/activate
DJANGO_SETTINGS_MODULE=core.test_settings python manage.py test apps.home.tests
```

Solo el módulo Form Builder:

```bash
DJANGO_SETTINGS_MODULE=core.test_settings python manage.py test \
    apps.home.tests.test_form_builder_schema \
    apps.home.tests.test_form_builder_security \
    apps.home.tests.test_form_builder_views \
    apps.home.tests.test_form_builder_templatetags \
    apps.home.tests.test_form_builder_parity
```

> El módulo `core.test_settings` evita la dependencia de `mysqlclient`
> usando SQLite en memoria. Para correr la suite contra MySQL real, omite
> el `DJANGO_SETTINGS_MODULE`.

### Frontend

Requiere conectividad a `registry.npmjs.org` para la primera instalación:

```bash
npm install
npm test           # corrida única
npm run test:watch # modo desarrollo
```

## Cobertura por capa

### `schema.py` (corazón del módulo)

| Función | Cobertura |
| --- | --- |
| `normalize_schema` | tolerancia a `None`, dict, str, lista, entradas no-dict |
| `visible_when_match` | operadores `equals` / `not_equals` / `contains`, coerción boolean, alias `value` vs `equals`, edge cases |
| `_parse_simple_value` | `number` (coma decimal, int, vacío, inválido), `checkbox`, `boolean`, `multiselect`, `text` |
| `_validate_leaf` | `required`, `min`, `max`, multiselect vacío, no numérico |
| `parse_post_to_answers` | required visible/oculto, repeater required/parseo, multiselect, indices no contiguos |
| `validate_and_parse_post` | integración IMC end-to-end |
| `apply_computed` | IMC normal, talla=0, falta dep, valor inválido, deps por defecto, fórmula genérica con `precision`, división por cero, walks en sections |
| `_safe_eval_arithmetic` | aritmética básica, división por cero, sintaxis inválida, fórmula vacía |

### Seguridad del sandbox de fórmulas

Vectores de inyección probados (todos rechazados):

- `__import__("os").system(...)`
- `os.system`, `open(...)`, `eval(...)`, `exec(...)`, `compile(...)`
- `globals()`, `locals()`, `help`, `print(...)`
- Walk de `__class__` / `__bases__` / `__subclasses__`
- `(lambda: __import__("os"))()`
- Identificador Unicode (`álpha`) fuera del allowlist
- Nombre extra fuera del allowlist incluso si la sintaxis es válida

Casos positivos (aceptados): aritmética básica, operadores bit-a-bit, potencia, unario menos.

### Vistas

- `ensure_schema_version`: crea v1, idempotente sin cambios, idempotente al reordenar claves, autoincremento al cambiar.
- `exam_builder_create`: requiere `nombre`, persiste el examen.
- `exam_builder_edit`: rechaza JSON inválido (no escribe el campo), acepta lista válida, `publicar=1` crea versión.
- `exam_builder_preview`: rechaza JSON inválido (400), devuelve HTML para esquema válido, requiere POST (403 en GET).
- `exam_builder_publish`: idempotente.
- `guardar_examen_builder`: éxito (`answers` + `computed` + estado=`completado`), validación falla (no crea submission), visita firmada (bloquea), versión congelada al guardar, re-guardado actualiza la submission.
- Constraints: `unique_together(examen,version)` y `OneToOne` de `ExamenSubmission`.

### Runtime JS

- Visibilidad: `equals`, `not_equals`, `contains` (lista y string), boolean, JSON malformado, atributos legacy, encadenamiento A→B→C.
- IMC: actualización en vivo, talla=0, falta peso, múltiples computados.
- Pestañas: redirige al ocultarse la activa, mantiene activa si su condición se cumple.
- Repeaters: agrega fila reescribiendo índices, idempotencia de `bindRepeaters`, checkbox/radio se desmarcan en la fila clonada, índices contiguos al agregar 3+.
- API: `init`, `refresh`, tolerancia a `null`.

### Paridad backend ↔ frontend

`tests/fixtures/visible_when_cases.json` es la **única fuente de verdad**
para casos de visibilidad. Si un día evoluciona la lógica de un operador,
basta con añadir un caso al JSON y ambos tests fallarán juntos hasta que
ambas implementaciones queden alineadas.

## Edge cases cubiertos

| Caso | Test |
| --- | --- |
| Inyección por fórmula | `test_rejects_dunder_import`, `test_rejects_getattr_dunder`, etc. |
| División por cero | `test_imc_zero_talla_skipped`, `test_generic_formula_division_by_zero_skipped`, `test_division_by_zero_returns_none`, IMC en JS con `talla=0` |
| Sección oculta con `required` adentro | `test_hidden_section_skips_required_inside` |
| Repeater required vacío | `test_repeater_required_empty_emits_error` |
| Repeater con índices no contiguos | `test_repeater_orders_rows_numerically` |
| Boolean coercion `false` con `0`/`""` | `test_equals_false_boolean` (backend), JS análogo |
| `visible_when` con campo inexistente | `test_equals_field_missing` |
| JSON malformado en `data-vw-cond` | `test_falls_back_to_visible_on_malformed_json` |
| Versión de esquema congelada al save | `test_save_freezes_schema_version_at_save_time` |
| Visita firmada bloquea guardado | `test_save_blocked_when_visita_firmada` |
| Reordenar claves no genera nueva versión | `test_idempotent_when_keys_reordered` |
| Identificador Unicode fuera del allowlist | `test_unicode_identifier_outside_allowlist_rejected` |

## Mantenimiento

- **Añadir un caso de visibilidad**: edita `tests/fixtures/visible_when_cases.json`. Backend (`test_form_builder_parity.py`) y frontend (`tests/js/parity.spec.js`) lo recogen automáticamente.
- **Refactor del sandbox de fórmulas**: corre primero `test_form_builder_security.py` para garantizar que no se introdujo un nuevo vector.
- **Cambios en `runtime.js`**: corre `npm test`. La suite carga el archivo real, sin mocks del runtime, así que cualquier regresión visible en producción debería reproducirse aquí.

## Próximos pasos sugeridos

- Property-based testing con Hypothesis para `_safe_eval_arithmetic` (genera identificadores aleatorios y verifica que ninguno fuera del whitelist se ejecute).
- Refactor de `builder.js` para exportar utilidades puras (`slugify`, `validateState`, `findNode`, `defaultNode`) como módulo ESM y testearlas directamente.
- Snapshot tests del `preview_fragment.html` con esquemas representativos del catálogo clínico real.
- CI: añadir un job que corra ambas suites en cada PR (ver `.github/workflows/`).
