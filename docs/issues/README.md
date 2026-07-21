# Backlog de Issues — Reunión Carlos / Daniel (Impresión, Formularios y Exportación)

Este backlog traduce la reunión de revisión del sistema **Atenea (HCE GRUNECO)** en tickets
ejecutables. Cada issue incluye contexto de la reunión, comportamiento actual, comportamiento
esperado, referencias técnicas al código y criterios de aceptación.

> Fuente: transcripción de reunión (revisión de impresión PDF, formularios de examen físico/
> neurológico, antecedentes, cuestionarios y exportación CSV).

## Épicas

### Épica A — Impresión / PDF (Resumen Digital de Atención)
| # | Título | Prioridad |
|---|--------|-----------|
| [A-01](A-01-membrete-normativo-todas-las-paginas.md) | Encabezado/membrete normativo "Resumen Digital de Atención" y repetición en todas las páginas | Alta |
| [A-02](A-02-reducir-tamano-letra-compactar-tablas.md) | Reducir tamaño de letra y compactar tablas del PDF | Media |
| [A-03](A-03-bloque-firma-profesional-pdf.md) | Bloque de firma profesional en el PDF (imagen + nombre + registro médico) | Alta |
| [A-04](A-04-seleccion-y-orden-de-impresion.md) | Selección de exámenes/campos a imprimir y definición del orden | Alta |
| [A-05](A-05-impresion-usa-variable-en-vez-de-etiqueta.md) | Impresión muestra el nombre de la variable en vez de la etiqueta | Alta |
| [A-06](A-06-encabezados-de-subseccion-en-impresion.md) | Encabezados de subsección en la impresión (pares craneales, etc.) | Media |
| [A-07](A-07-ultima-fila-tabla-como-total.md) | Última fila de tablas impresa como "total" por error | Media |

### Épica B — Formularios (examen físico/neurológico, antecedentes, cuestionarios)
| # | Título | Prioridad |
|---|--------|-----------|
| [B-08](B-08-estandarizar-toggles-examen-fisico.md) | Estandarizar toggles de examen físico/neurológico (normal/anormal, presente/ausente, detecta) | Alta |
| [B-09](B-09-boton-evaluado-no-evaluado.md) | Botón "Evaluado / No evaluado" por sección en examen físico/neurológico | Alta |
| [B-10](B-10-puntaje-total-y-subescalas-faltantes.md) | Puntaje total y subescalas faltantes en formularios (AQD, etc.) | Alta |
| [B-11](B-11-editar-formularios-legacy-no-carga-datos.md) | Bug: al editar formularios legacy no cargan los datos guardados | Alta |
| [B-12](B-12-antecedentes-campos-no-se-guardan.md) | Bug: campos de Antecedentes no se guardan/muestran completos | Media |
| [B-13](B-13-estandarizar-nombres-variables-etiquetas.md) | Estandarizar nombres de variables y etiquetas en formularios | Baja |
| [B-13 inventario](B-13-inventario-nombres-parcial.md) | Inventario parcial de nombres (sin renombres; entregable Épica B) | Baja |

### Épica C — UX / Exportación
| # | Título | Prioridad |
|---|--------|-----------|
| [C-14](C-14-paginacion-listado-pacientes.md) | Paginación/navegación del listado (scroll horizontal) | Baja |
| [C-15](C-15-exportacion-csv-seleccion-por-examen.md) | Exportación CSV: selección de campos por examen (total vs ítems) | Alta |

## Estado de implementación — Épica A (implementada)

| # | Estado | Notas de implementación |
|---|--------|-------------------------|
| A-01 | ✅ Hecho | Título del membrete → "SISTEMA DE RESUMEN DIGITAL DE ATENCIÓN"; nombre + documento del paciente en el encabezado; membrete y pie ahora son *running elements* (`position: running`) repetidos en todas las páginas vía `@top-center`/`@bottom-center` en `apps/static/pdf/print.css`. |
| A-02 | ✅ Hecho | Fuente base 8.5 pt y padding de tablas reducido en `print.css`. |
| A-03 | ✅ Hecho | Nuevo campo `UserProfile.registro_medico` (migración `0010_userprofile_registro_medico`); parcial `pdf/partials/firma_profesional.html`; contexto en `hc_pdf.py` (`firma_img`, `registro_medico`). **Falta aplicar migración**: `python manage.py migrate`. |
| A-04 | ✅ Hecho | Pantalla `info_paciente/seleccionar_impresion.html` (checkboxes + reordenar ↑/↓); vista `seleccionar_impresion_visita` y ruta `visita/<id>/imprimir/`; `generar_pdf_historia_clinica_visita` acepta `examen_ids`. |
| A-05 | ✅ Hecho | Valores legibles en la vista genérica: `choices` → texto (`get_..._display`), booleanos `True`→"Sí"; respuestas de *submission* mapeadas a sus etiquetas del esquema. Etiquetas provenientes de `verbose_name`. **Etiquetas completadas desde los templates de captura** (pregunta real como `verbose_name`): AQD Cuidador/Participante, NPI Cuidador, MEW, Examen Físico de Sueño, **CDR Cuidador** (6 dominios + `PRINT_SECCIONES_INICIOS`) y **CDR Participante** (3 dominios + secciones). Normalización de valores crudos `si`/`no`/`correcto`→Sí/No/Correcto en `_formatear_valor_campo`. Migraciones `0011`/`0012`. |
| A-06 | ✅ Hecho (neurológico) | Agrupación por subsección en `resultado_generico.html` + `ExamenNeurologicoResult.PRINT_SECCIONES_INICIOS` (I–XII pares, sensibilidad, reflejos, fuerza, coordinación, marcha, mov. anormales). Mecanismo genérico reutilizable (con *catch-all*, sin pérdida de campos). El examen físico (id 3) puede sumarse con el mismo patrón. |
| A-07 | ✅ Hecho | Se eliminó el resaltado de "total" en `tr:last-child`; ahora solo aplica a filas con clase `.hc-fila-total`. |

> **Pendiente de verificación visual**: WeasyPrint no está instalado en el entorno de desarrollo usado; el HTML y el CSS se validaron y siguen el patrón documentado de *running elements* de WeasyPrint. Se recomienda generar un PDF real (visita firmada y de ≥ 2 páginas) para confirmar encabezado/pie repetidos y márgenes.

## Estado de implementación — Épica B (parcial; no cerrada)

| # | Estado | Notas de implementación |
|---|--------|-------------------------|
| B-08 | 🟡 Parcial avanzado | `FIELD_TOGGLE_SEMANTICS` + `formatear_toggle()`; defaults normales; etiquetas en captura; impresión True/False. Precarga físico alineada (`pared_abdominal_normal/_anormal`, `masas`/`megalias` booleanos; `value="anormal"` sin espacio). Migración `0013`. **Pendiente Carlos:** mapeo formal campo→detecta/síntoma/estructura. |
| B-09 | 🟡 Parcial avanzado | Flags `seccion_*_evaluado`; JS `applySeccionEvaluado()` oculta y **deshabilita** inputs; etiqueta dinámica Evaluado/No evaluado; impresión “Sección: No evaluado”. **Pendiente:** QA de aceptación y tests E2E de persistencia. |
| B-10 | 🟡 Parcial avanzado | `puntaje_total` AQD/RedLat; `suma_cajas` CDR; vista/impresión; export CSV con subescalas. **Vista/PDF:** sin caja de total en Yesavage/AQD/RedLat; CDR resalta **CDR Global** + subtítulo «Suma de los 6 dominios» calculada en vivo (corrige 0 en registros antiguos). **Pendiente Carlos:** inventario total de cuestionarios. |
| B-11 | 🟡 Parcial | `build_datos_examen_edicion()` + dispatch; tests de precarga neurológico, físico (pared/masas/megalias) y antecedentes. **Pendiente:** verificación en prod/datos reales; cobertura del resto de legacy. |
| B-12 | 🟡 Parcial avanzado | Subcampos patológicos en guardado/precarga/ver/print; tóxicos vía `get_tipos_display`; alérgicos/traumáticos usan `descripcion`/`fecha_inicio`; epidemiológicos muestran observaciones y alias de precarga `descripcion`↔`tipo_antecedente`. **Pendiente:** ciclo E2E completo en entorno clínico. |
| B-13 | 🟡 Parcial (explícito) | Entregable: [B-13-inventario-nombres-parcial.md](B-13-inventario-nombres-parcial.md) — inventario liviano **sin renombres**. Impresión ya usa `verbose_name` (A-05). **Pendiente Carlos:** inventario exhaustivo + decisión renombrar variables vs. solo etiquetas. |

> **Cierre de épica bloqueado** hasta: (1) refinos de mapeo/inventarios con Carlos, (2) QA de aceptación en entorno con datos reales. Gaps técnicos locales de B-08…B-12 abordados en esta pasada. **Falta aplicar migración**: `python manage.py migrate` (`0013_epic_b_toggles_evaluado_scores`).

## Estado de implementación — Épica C (implementada en ramas dedicadas)

| # | Estado | Rama / Notas de implementación |
|---|--------|--------------------------------|
| C-15 | ✅ Hecho | Rama `feature/c-15-export-csv-por-examen`. Servicio `apps/home/services/project_csv_export.py` (catálogo por examen, POST namespaced `campos_examen_<id>`, fallback lista global, legacy + builder, tablas JSON, preserva `0`/`False`). Overrides `export` en `exam_registry.py` (CDR, RedLat, MEW, tablas). UI por examen en `exportar_proyecto_form.html`. Vista `exportar_csv_proyecto` adelgazada a orquestación. Tests: `apps/home/tests/test_project_csv_export.py`. |
| C-14 | ✅ Hecho | Rama `feature/c-14-paginacion-listado-pacientes`. `lista_pacientes`: orden estable, `prefetch_related("proyectos")`, búsqueda GET `q` (documento/nombres/proyectos/códigos), filtro `proyecto`, `Paginator(25)`, códigos solo de la página, `pagination_query` conserva filtros. UI: formulario GET, parcial `includes/pagination.html`, responsive tipo tarjeta &lt;768px (`data-label`) sin scroll horizontal. Tests: `apps/home/tests/test_patient_list.py`. |

> **Notas:** No se mezclan C-14 y C-15 en un solo PR. No hay migraciones nuevas ni perfiles de exportación persistidos. Criterios de aceptación de ambos issues quedan cubiertos a nivel código/tests; falta QA visual en entorno clínico.

## Convenciones
- **Prioridad**: Alta (bloquea uso clínico/normativo), Media (mejora relevante), Baja (calidad de vida).
- **Referencias técnicas**: rutas y funciones reales del repo al momento de redactar el backlog.
- El motor de PDF activo es **WeasyPrint** (`apps/home/services/hc_pdf.py`); ReportLab
  (`apps/home/views/pdf.py`) es solo *fallback* legacy. Los cambios de impresión deben priorizar WeasyPrint.
