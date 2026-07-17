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
| A-05 | ✅ Hecho | Valores legibles en la vista genérica: `choices` → texto (`get_..._display`), booleanos `True`→"Sí"; respuestas de *submission* mapeadas a sus etiquetas del esquema. Etiquetas ya provenían de `verbose_name`. |
| A-06 | ✅ Hecho (neurológico) | Agrupación por subsección en `resultado_generico.html` + `ExamenNeurologicoResult.PRINT_SECCIONES_INICIOS` (I–XII pares, sensibilidad, reflejos, fuerza, coordinación, marcha, mov. anormales). Mecanismo genérico reutilizable (con *catch-all*, sin pérdida de campos). El examen físico (id 3) puede sumarse con el mismo patrón. |
| A-07 | ✅ Hecho | Se eliminó el resaltado de "total" en `tr:last-child`; ahora solo aplica a filas con clase `.hc-fila-total`. |

> **Pendiente de verificación visual**: WeasyPrint no está instalado en el entorno de desarrollo usado; el HTML y el CSS se validaron y siguen el patrón documentado de *running elements* de WeasyPrint. Se recomienda generar un PDF real (visita firmada y de ≥ 2 páginas) para confirmar encabezado/pie repetidos y márgenes.

## Convenciones
- **Prioridad**: Alta (bloquea uso clínico/normativo), Media (mejora relevante), Baja (calidad de vida).
- **Referencias técnicas**: rutas y funciones reales del repo al momento de redactar el backlog.
- El motor de PDF activo es **WeasyPrint** (`apps/home/services/hc_pdf.py`); ReportLab
  (`apps/home/views/pdf.py`) es solo *fallback* legacy. Los cambios de impresión deben priorizar WeasyPrint.
