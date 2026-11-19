## Learned User Preferences

- Prefiere comunicación e implementación en español.
- En impresión/PDF de HC: membrete alineado al Word de referencia; cuerpo y respuestas como en la vista "ver"; no repetir en el cuerpo datos que ya van en el membrete; evitar páginas en blanco.
- En impresión, usar `verbose_name` (etiquetas legibles) para nombres de examen y preguntas, no nombres de variable/campo.
- En la vista "ver" de exámenes, sin scroll horizontal: el contenido debe adaptarse al ancho de pantalla.
- Formularios legacy: no editables desde el form builder (sin botón de edición); cambios de campos solo por código.
- Campos computados del form builder: visibles en vista previa; ocultos durante el llenado por el paciente.
- Secciones como pestañas solo en previsualización/llenado; en el editor de creación las secciones se mantienen como están.
- Issues/tickets en markdown (`docs/issues/`); prefiere planes por fases con nombres de ramas y épicas antes de cambios grandes.
- En exportación CSV de proyectos, campos tipo tabla deben salir como JSON (parámetro + resultado); en AQD exportar ambos totales (acompañante y participante), el delta y la interpretación de conciencia de enfermedad.
- Puntajes en vista/impresión: sin caja genérica de «Puntaje total» en Yesavage ni AQD; en AQD mostrar el bloque de conciencia (totales acompañante/participante, delta e interpretación) cuando ambos existen en la misma visita; en RedLat Spanish solo puntajes por dominio/componente; en CDR Evaluación Clínica mostrar CDR Global y la suma de los 6 dominios; en Sueño MEW (matutinidad/vespertinidad) mostrar «Puntuación total MEQ».
- En toggles de examen (Presente/Ausente u equivalentes), mostrar siempre el nombre de la pregunta junto a las etiquetas del toggle; no dejar solo Presente/Ausente.
- En Recuérdame/PostHog: no instrumentar `identify` para enlazar usuarios; preferir puente autenticado (API/Mongo) o cruce por calendario clínico.

## Learned Workspace Facts

- Proyecto Django clínico ATENEA (`WEB-AteneaGruneco`, org Gruneco-Clinico) con módulos de pacientes, visitas, exámenes, agendamiento y proyectos; despliegue Testing/Production vía GitHub Actions a Bitnami; backlog en `docs/issues/` (A PDF, B formularios, C exportación/UX).
- Conviven exámenes legacy (`campos` JSON) y form builder; legacy sin edición en el builder; nombres con guiones bajos (p. ej. `General_Antecedentes`) — no renombrar al azar.
- Impresión HC/PDF con WeasyPrint (`apps/home/services/hc_pdf.py`, `apps/static/pdf/print.css`, `apps/templates/pdf/`); membrete «Resumen Digital de Atención» (no «Historia Clínica») en todas las páginas.
- Épica B (formularios): toggles tipados (`FIELD_TOGGLE_SEMANTICS` / `field_toggle_semantics.py`), secciones Evaluado/No evaluado en examen físico/neurológico, precarga de edición legacy vía `exam_edit_context.py`.
- Épica C (exportación/UX): CSV con selección por examen; listado de pacientes compacto con paginación en el contenedor; formulario de exportación sin solapamiento de etiquetas largas.
- AQD (AQ-D): delta = total acompañante/cuidador − total participante (≥10 → SIN CONCIENCIA DE ENFERMEDAD; <10 → CON CONCIENCIA DE ENFERMEDAD; negativos válidos); solo si ambos AQD están en la misma visita; ítems «2. A veces» deben parsear el entero inicial.
- Plan de visitas programadas: frecuencias diario/semanal/L-V/personalizado/fechas específicas (`plan_visitas.py`, modal en `pacient.html`); la página mezcla Bootstrap 4 y 5, lo que afecta selects del modal.
- Dominios frecuentes: calendario de disponibilidad/salas, plan de visitas, caracterización del sueño en seguimientos, anosognosia (AQD/CDR), exportación de proyectos.
- Dashboard Recuérdame (biomarcadores digitales): PostHog (MCP/endpoints); descarga de uso en un único archivo con todos los usuarios; se busca mayor interactividad en las gráficas.
- Cruce Anosognosia × RecuérdaMe: examen form builder id 56 (`Interv_fecha` + correo del paciente) enriquecido con biomarcadores PostHog; CSV único en `estadisticas/anosognosia-cruce.csv` (`recuerdame_anosognosia_cruce.py`); el match histórico por email en PostHog es débil (casi anónimo).
- Actividad autenticada RecuérdaMe→Atenea: `POST /v1/integrations/atenea/activity` con API key (`ATENEA_INTEGRATION_API_KEY` / `RECUERDAME_ATENEA_API_KEY`); ruta pública (los `/internal/*` no salen por el proxy); paquete users + login_logs + sessionGame; cliente `recuerdame_activity_api.py`.
