# A-03 — Bloque de firma profesional en el PDF (imagen + nombre + registro médico)

- **Épica:** A — Impresión / PDF
- **Tipo:** bug / cumplimiento normativo
- **Prioridad:** Alta
- **Componentes:** PDF, firma, perfil de usuario

## Contexto (reunión)
Toda historia/resumen debe ir **firmado por un profesional**. Al firmar una visita
(icono "coronita", visible solo a perfiles profesional/administrativo), la visita queda cerrada:
ya no se puede editar, solo agregar **notas aclaratorias**. En la impresión, al final del documento
debe aparecer el bloque de firma del profesional que firmó:
- Recuadro de **firma electrónica** (imagen guardada en el perfil de Atenea).
- **Nombre completo** del firmante.
- **Registro médico** del profesional.

Actualmente ese bloque **no aparece** al final de varios PDFs (se ve el evaluador/joven investigador,
pero no el bloque de firma del profesional).

## Comportamiento actual
- La plantilla principal WeasyPrint (`apps/templates/pdf/historia_clinica.html`) muestra `firmante`
  solo como texto dentro de la tabla "Información de la atención"; **no** renderiza un bloque de firma
  con imagen ni registro médico.
- El bloque de firma con imagen base64 solo existe en el *fallback* ReportLab:
  `_build_signature_section()` en `apps/home/views/pdf.py`, que lee `UserProfile.firma` (base64).
- El modelo `UserProfile` (`apps/home/models/patient.py`) solo tiene `firma` (base64); **no existe
  campo de registro médico**.

## Comportamiento esperado
1. Agregar al final del PDF WeasyPrint un bloque de firma cuando `visita.firmado_por` existe:
   imagen de la firma (base64 desde `UserProfile.firma`), nombre completo y registro médico.
2. Agregar un campo `registro_medico` (o `tarjeta_profesional`) al perfil de usuario y exponerlo
   en el contexto del PDF.
3. El bloque debe aparecer siempre que la visita esté firmada, en todos los tipos de examen.

## Referencias técnicas
- Contexto PDF: `render_historia_clinica_html()` en `apps/home/services/hc_pdf.py` (agregar
  `firma_img`, `registro_medico`).
- Plantilla: `apps/templates/pdf/historia_clinica.html` (agregar sección de firma antes del pie).
- Modelo firma: `UserProfile` en `apps/home/models/patient.py` (agregar `registro_medico`;
  requiere migración).
- Referencia de decodificación base64: `_build_signature_section()` en `apps/home/views/pdf.py`.

## Criterios de aceptación
- [ ] Al imprimir una visita firmada, aparece el recuadro de firma con la imagen del perfil.
- [ ] Aparecen nombre completo y registro médico del profesional firmante.
- [ ] Se muestra en todos los exámenes/visitas firmadas (no solo en algunos).
- [ ] Migración creada para el campo de registro médico del perfil.
