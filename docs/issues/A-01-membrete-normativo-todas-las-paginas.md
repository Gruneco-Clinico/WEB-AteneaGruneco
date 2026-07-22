# A-01 — Encabezado/membrete normativo "Resumen Digital de Atención" y repetición en todas las páginas

- **Épica:** A — Impresión / PDF
- **Tipo:** enhancement / cumplimiento normativo
- **Prioridad:** Alta
- **Componentes:** PDF, membrete

## Contexto (reunión)
Con la nueva normativa de interoperabilidad/sincronización, el documento **ya no se llama
"Historia Clínica"** sino **"Sistema de Resumen Digital de Atención"**. El encabezado debe
contener, según el modelo enviado en Word:
- Título: *Resumen Digital de Atención*.
- Nombre completo y documento del paciente **arriba** (además de la identificación que ya va abajo).
- El **membrete** (logo UdeA, logo/datos GRUNECO, grupo y dirección) debe repetirse **en todas las
  hojas**, no solo en la primera. Igual el pie institucional.

## Comportamiento actual
- El membrete dice `HISTORIA CLÍNICA ELECTRÓNICA` y solo se incluye una vez, al inicio del documento.
- El pie institucional también aparece una sola vez, al final.

Referencias:
- `apps/templates/pdf/partials/membrete.html` → texto `HISTORIA CLÍNICA ELECTRÓNICA`.
- `apps/templates/pdf/partials/pie_institucional.html` → datos del grupo/dirección.
- `apps/templates/pdf/historia_clinica.html` → incluye membrete y pie una sola vez en el flujo.
- `apps/home/services/hc_pdf.py` → `render_historia_clinica_html` arma el contexto y `_load_print_css()` carga `apps/static/pdf/print.css`.

## Comportamiento esperado
1. Cambiar el título del membrete a **"Resumen Digital de Atención"** (revisar wording exacto contra el Word).
2. Incluir en el encabezado el **nombre completo + tipo y número de documento** del paciente
   (ya disponibles como `nombre_completo` y `documento_identidad` en el contexto de `hc_pdf.py`).
3. Repetir membrete y pie institucional **en cada página** del PDF, usando encabezados/pies de
   página fijos de WeasyPrint vía CSS `@page` (`@top-center`, `@bottom-center`) con
   `position: running(...)` o elementos `running header/footer`.

## Referencias técnicas / implementación sugerida
- Definir en `apps/static/pdf/print.css` reglas `@page { @top-center { content: element(membrete); } @bottom-center { content: element(pie); } }`
  y marcar los bloques con `position: running(membrete)` / `running(pie)`.
- El nombre y documento del paciente ya se pasan al contexto (`nombre_completo`, `documento_identidad`).

## Criterios de aceptación
- [ ] El título ya no dice "Historia Clínica"; dice "Resumen Digital de Atención" (texto confirmado con el Word).
- [ ] El encabezado muestra nombre completo y documento del paciente.
- [ ] Membrete (logos + grupo + dirección) visible en todas las páginas del PDF.
- [ ] Pie institucional visible en todas las páginas.
- [ ] Verificado en un PDF de ≥ 2 páginas generado con WeasyPrint.
