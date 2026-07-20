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
- En exportación CSV de proyectos, campos tipo tabla deben salir como JSON (parámetro + resultado).

## Learned Workspace Facts

- Proyecto Django clínico ATENEA (`WEB-AteneaGruneco`, org Gruneco-Clinico) con módulos de pacientes, visitas, exámenes, agendamiento y proyectos.
- Conviven exámenes legacy (`campos` JSON) y el módulo form builder / exam schema; los legacy deben seguir funcionando sin edición en el builder.
- Despliegue a ramas Testing y Production vía GitHub Actions hacia servidores Bitnami.
- Impresión de historia clínica/PDF con WeasyPrint (`apps/home/services/hc_pdf.py`, `apps/static/pdf/print.css`, plantillas en `apps/templates/pdf/`).
- El membrete normativo debe titularse como "Resumen Digital de Atención" (no "Historia Clínica") y repetirse en todas las páginas.
- Backlog de épicas/issues en `docs/issues/` (A impresión/PDF, B formularios/exámenes, C exportación/UX).
- Nombres de exámenes legacy suelen usar guiones bajos (p. ej. `General_Antecedentes`); no renombrar al azar o dejan de resolverse.
- Dominios frecuentes: calendario de disponibilidad/salas, caracterización del sueño en seguimientos, anosognosia (AQD/CDR), y exportación del módulo de proyectos.
