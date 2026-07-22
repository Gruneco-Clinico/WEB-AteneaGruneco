# B-13 — Inventario liviano de nombres de variables (sin renombres)

- **Épica:** B — Formularios
- **Estado:** inventario parcial (sin renombres masivos)
- **Fecha:** 2026-07-20

## Alcance

Solo documentación. Los `verbose_name` ya cubren impresión (A-05). Renombres de
campos en BD quedan para refinamiento con Carlos.

## Hallazgos (legacy / builder)

| Área | Ejemplo | Observación |
|------|---------|-------------|
| Neurológico | `tacto_frente_globo`, `mimica_elevacion_nasal` | Nombres técnicos; UI usa etiquetas anatómicas |
| Neurológico | verbose_name aún dice “alterado” en varios campos | Semántica B-08 imprime Normal/Anormal; alinear verbose pendiente Carlos |
| Físico | pares `*_normal` / `*_anormal` | Redundantes para impresión; B-08 solo mapea `*_normal` + síntomas |
| AQD | campos sin prefijo de dominio | OK para score; textos largos en verbose_name |
| RedLat | `bano`, `aseo_hogar` | Abreviaturas; verbose_name legible |
| Builder | ids de campo en `Examen.campos` | Independientes de modelos legacy |

## Hecho en Épica B (relacionado)

- B-08: `FIELD_TOGGLE_SEMANTICS` + impresión True/False; precarga físico (`pared_abdominal_*`, masas/megalias)
- B-09: flags `seccion_*_evaluado`; UI Evaluado/No evaluado + disable de inputs
- B-10: `puntaje_total` AQD/RedLat, `suma_cajas` CDR; export CSV subescalas; cero no se pierde
- B-11/B-12: precarga edición; ver/print tóxicos/alérgicos/traumáticos/epidemiológicos alineados

## Pendiente Carlos

1. Mapeo formal campo → detecta/síntoma/estructura (refinar lista inicial).
2. Inventario total de cuestionarios anosognosia (subescalas faltantes).
3. Decisión de renombres vs. solo `verbose_name`.

> Sin estos tres puntos la Épica B **no se cierra**; el inventario de este archivo permanece parcial a propósito.
