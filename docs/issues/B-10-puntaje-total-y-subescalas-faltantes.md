# B-10 — Puntaje total y subescalas faltantes en formularios (AQD, etc.)

- **Épica:** B — Formularios
- **Tipo:** bug / enhancement
- **Prioridad:** Alta
- **Componentes:** Cuestionarios (anosognosia), impresión, exportación

## Contexto (reunión)
Algunos formularios **no tienen puntaje total** (ej.: **AQD**), y como la impresión/exportación solo
muestra el total cuando existe, no se imprime nada de score. Se debe revisar formulario por formulario
para agregar el total donde falte. También hay formularios con **subescalas** además del total:
- **CDR**: tiene un puntaje total (algoritmo, no suma) y además "suma de cajas" (sí es suma de ítems).
- **RedLat (RedLatSpanish)**: da un puntaje por cada uno de ~6 componentes, más el total.

Carlos revisará todos los cuestionarios de anosognosia (donde está el grueso) para identificar cuáles
requieren total y/o subescalas.

## Comportamiento actual
- La impresión toma `puntaje_total`/`puntuacion_total` si existe; si no, no muestra score
  (`get_context_ver_examen()` en `apps/home/services/exam_view_context.py`;
  `_extract_exam_data()` en `apps/home/views/pdf.py`).
- Formularios sin campo de total no lo calculan ni lo muestran.

## Comportamiento esperado
1. Agregar cálculo/almacenamiento de puntaje total en los formularios que lo requieran (ej.: AQD).
2. Soportar y mostrar **subescalas** (CDR suma de cajas; RedLat por componente) además del total.
3. Que impresión y exportación puedan reflejar total y subescalas.

## Referencias técnicas
- Modelos de cuestionarios en `apps/home/models/results_anosognosia.py`
  (ej.: `AQDCuidadorResult` id 30, `AQDParticipanteResult` id 31, `RedLatSpanishResult` id 32,
  `CDRCuidadorResult`/`CDRParticipanteResult` id 33/34, `PuntajeCDRResult` id 35).
- Ver `apps/home/exam_registry.py` para el mapeo id→modelo.

## Dependencias
- Carlos entrega la lista de formularios que necesitan total/subescala y su fórmula.

## Criterios de aceptación
- [ ] AQD (cuidador y participante) calcula y muestra puntaje total.
- [ ] CDR muestra total + suma de cajas.
- [ ] RedLat muestra puntaje por componente + total.
- [ ] Impresión y exportación reflejan total y subescalas.
- [ ] Inventario de formularios revisados con estado (tiene total / falta / N/A).
