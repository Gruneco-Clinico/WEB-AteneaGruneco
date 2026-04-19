# Rollout Form Builder

## Requisitos

1. Aplicar migraciones: `python manage.py migrate home`
2. Rol **staff** para `/builder/examenes/`

## Convivencia con legacy

- Exámenes con `examen_id` en `apps/home/exam_legacy.py` siguen usando plantillas y modelos `*Result`.
- Cualquier **otro** `Examen` en BD con `campos` (lista JSON no vacía) se renderiza con el template genérico y guarda en `ExamenSubmission`.

## Pasos operativos

1. Crear o elegir un `Examen` (p. ej. desde Django admin o datos existentes) con `id` **no** legacy (típicamente > 40 o un id libre en tu BD).
2. En **Form Builder** (`/builder/examenes/`), editar el examen y pegar el JSON de `campos` (ver `FORM_BUILDER_SCHEMA.md`).
3. Opcional: **Publicar versión de esquema** para registrar `ExamenSchemaVersion`.
4. Asignar el examen a visitas: editar `TipoVisita.examenes` (JSON) en `/builder/tipo-visita/<id>/examenes/` o por el flujo habitual de proyectos, asegurando que al crear la visita se generen filas `VisitaExamen` para ese `Examen`.
5. El usuario abre el examen desde el detalle del paciente; al guardar, el estado pasa a `completado` y los datos quedan en `ExamenSubmission`.
6. Ver resultado: misma URL que otros exámenes (`ver_resultado_examen`); el backend detecta envío builder y muestra `resultado_builder.html`.

## Prueba mínima (smoke)

1. Migrar BD.
2. Staff: crear examen con `campos` mínimo:
   ```json
   [{"type":"section","label":"Prueba"},{"id":"nota","type":"text","label":"Nota","required":true}]
   ```
3. Asociar a un tipo de visita y crear visita con ese examen.
4. Completar formulario y verificar fila en `home_examensubmission`.

## Archivos clave

| Área | Ruta |
|------|------|
| Legacy IDs | `apps/home/exam_legacy.py` |
| Modelos | `apps/home/models/exam_builder.py` |
| Validación / IMC | `apps/home/form_builder/schema.py` |
| Vistas | `apps/home/views/exam_builder.py` |
| Dispatch | `apps/home/views/exams_dispatch.py` (`realizar_examen`, `ver_resultado_examen`) |
| `esta_realizado` | `apps/home/models/visit.py` |
