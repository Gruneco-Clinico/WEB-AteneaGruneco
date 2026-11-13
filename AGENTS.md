## Learned User Preferences

- Prefiere comunicación e implementación en español.
- En impresión/PDF de HC: membrete alineado al Word de referencia; cuerpo y respuestas como en la vista "ver"; no repetir en el cuerpo datos que ya van en el membrete; evitar páginas en blanco.
- En impresión, usar `verbose_name` (etiquetas legibles) para nombres de examen y preguntas, no nombres de variable/campo.
- En la vista "ver" de exámenes, sin scroll horizontal: el contenido debe adaptarse al ancho de pantalla.
- Formularios legacy: no editables desde el form builder (sin botón de edición); cambios de campos solo por código.
- Campos computados del form builder: visibles en vista previa; ocultos durante el llenado por el paciente.
- Secciones como pestañas solo en previsualización/llenado; en el editor de creación las secciones se mantienen como están.
- Issues y tickets del trabajo se mantienen en markdown dentro del repo (`docs/issues/`).
- Prefiere planes por fases con nombres de ramas y épicas antes de implementar cambios grandes.
- En exportación CSV de proyectos, campos tipo tabla deben salir como JSON (parámetro + resultado); en AQD exportar ambos totales (acompañante y participante), el delta y la interpretación de conciencia de enfermedad.
- Puntajes en vista/impresión: sin caja genérica de «Puntaje total» en Yesavage ni AQD; en AQD mostrar el bloque de conciencia (totales acompañante/participante, delta e interpretación) cuando ambos existen en la misma visita; en RedLat Spanish solo puntajes por dominio/componente; en CDR Evaluación Clínica mostrar CDR Global y la suma de los 6 dominios; en Sueño MEW (matutinidad/vespertinidad) mostrar «Puntuación total MEQ».
- En toggles de examen (Presente/Ausente u equivalentes), mostrar siempre el nombre de la pregunta junto a las etiquetas del toggle; no dejar solo Presente/Ausente.

## Learned Workspace Facts

- Proyecto Django clínico ATENEA (`WEB-AteneaGruneco`, org Gruneco-Clinico) con módulos de pacientes, visitas, exámenes, agendamiento y proyectos.
- Conviven exámenes legacy (`campos` JSON) y el módulo form builder / exam schema; los legacy deben seguir funcionando sin edición en el builder.
- Despliegue a ramas Testing y Production vía GitHub Actions hacia servidores Bitnami.
- Impresión de historia clínica/PDF con WeasyPrint (`apps/home/services/hc_pdf.py`, `apps/static/pdf/print.css`, plantillas en `apps/templates/pdf/`).
- El membrete normativo debe titularse como "Resumen Digital de Atención" (no "Historia Clínica") y repetirse en todas las páginas.
- Backlog de épicas/issues en `docs/issues/` (A impresión/PDF, B formularios/exámenes, C exportación/UX).
- Nombres de exámenes legacy suelen usar guiones bajos (p. ej. `General_Antecedentes`); no renombrar al azar o dejan de resolverse.
- Dominios frecuentes: calendario de disponibilidad/salas, plan de visitas programadas, caracterización del sueño en seguimientos, anosognosia (AQD/CDR), y exportación del módulo de proyectos.
- Épica B (formularios): toggles tipados (`FIELD_TOGGLE_SEMANTICS` / `field_toggle_semantics.py`), secciones Evaluado/No evaluado en examen físico/neurológico, y precarga de edición legacy vía `exam_edit_context.py`.
- Épica C (exportación/UX): CSV con selección por examen; listado de pacientes con layout compacto y paginación dentro del contenedor de la lista (visible sin scroll excesivo); formulario de exportación debe acomodar etiquetas largas sin solaparse.
- AQD (AQ-D): delta = total acompañante/cuidador − total participante (≥10 → SIN CONCIENCIA DE ENFERMEDAD; <10 → CON CONCIENCIA DE ENFERMEDAD; negativos válidos); solo si ambos AQD están en la misma visita; ítems pueden guardarse como «2. A veces» y el total debe parsear el entero inicial.
- Plan de visitas programadas: frecuencias diario/semanal/L-V/personalizado/fechas específicas (`plan_visitas.py`, modal en `pacient.html`); la página mezcla Bootstrap 4 y 5, lo que afecta el comportamiento de selects del modal.
