# A-02 — Reducir tamaño de letra y compactar tablas del PDF

- **Épica:** A — Impresión / PDF
- **Tipo:** enhancement / UI
- **Prioridad:** Media
- **Componentes:** PDF, CSS de impresión

## Contexto (reunión)
El PDF actual usa letra tamaño ~12 y ocupa demasiado espacio. Se pide reducir el tamaño de fuente
(referencia: tipo 9, legible) y compactar las tablas (menos ancho/espaciado) para que el documento
no quede tan extenso, como los recibos/historias clínicas tradicionales.

## Comportamiento actual
- Tipografía y espaciado del PDF definidos en `apps/static/pdf/print.css` (cargado por
  `_load_print_css()` en `apps/home/services/hc_pdf.py`).
- El *fallback* ReportLab define fuentes en `_make_styles()` (`apps/home/views/pdf.py`), pero no es
  la ruta principal.

## Comportamiento esperado
1. Reducir el tamaño base de fuente del PDF a ~9 pt (manteniendo legibilidad).
2. Compactar celdas de tablas: reducir padding y anchos, permitir tablas más ajustadas.
3. Asegurar que títulos/encabezados sigan jerárquicamente diferenciados aunque más pequeños.

## Referencias técnicas
- `apps/static/pdf/print.css` (fuente principal de estilos del PDF WeasyPrint).
- Clases usadas en plantillas: `.tabla-hc`, `.celda-hc`, `.fila-titulo-hc` (`apps/templates/pdf/partials/campo_hc.html`, `historia_clinica.html`).

## Criterios de aceptación
- [ ] Fuente base del PDF ≈ 9 pt.
- [ ] Tablas más compactas (menor padding/altura de fila).
- [ ] El documento resultante es notablemente más corto en número de páginas para la misma visita.
- [ ] Sigue siendo legible al imprimir en tamaño carta.
