"""
Management command: copiar_resultados_sueno
--------------------------------------------
Copia los resultados de exámenes desde las visitas TipoVisita=7
(Proyecto Sueño) a las visitas TipoVisita=20 (Caracterización Sueño)
que fueron creadas por migrar_pacientes_sueno pero quedaron vacías.

Para cada paciente:
  1. Busca la visita origen (TV=7) y la visita destino (TV=20).
  2. Para cada VisitaExamen en destino, busca el mismo examen en origen.
  3. Si origen tiene resultado, lo clona al VisitaExamen de destino.
  4. También clona modelos hijos (SuenoAnamnesis children, etc.).
  5. Manejo especial de Antecedentes (modelo por paciente, via link).

Operación idempotente:
  - Si el destino ya tiene resultado, lo omite.
  - Puede ejecutarse múltiples veces sin duplicar datos.

Uso:
  python manage.py copiar_resultados_sueno            # dry-run
  python manage.py copiar_resultados_sueno --ejecutar  # aplica cambios
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.home.models import (
    DatosDemograficos,
    TipoVisita,
    Visita,
    VisitaExamen,
)
from apps.home.models.results_general import AntecedentesResult, AntecedentesVisitaLink


# ── Configuración ────────────────────────────────────────────────────────
TIPO_VISITA_ORIGEN_ID = 7
TIPO_VISITA_DESTINO_ID = 20


class Command(BaseCommand):
    help = (
        "Copia resultados de exámenes de visitas TipoVisita=7 a las "
        "visitas TipoVisita=20 creadas por la migración anterior."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--ejecutar",
            action="store_true",
            default=False,
            help="Aplica cambios realmente. Sin flag = dry-run.",
        )

    # ── Helpers ───────────────────────────────────────────────────────────
    def _log(self, msg, style=None):
        if style:
            self.stdout.write(style(msg))
        else:
            self.stdout.write(msg)

    def _ok(self, msg):
        self._log(msg, self.style.SUCCESS)

    def _warn(self, msg):
        self._log(msg, self.style.WARNING)

    def _err(self, msg):
        self._log(msg, self.style.ERROR)

    # ── Clonado genérico de un resultado ──────────────────────────────────
    def _clone_result(self, source_resultado, dest_visita_examen, ejecutar):
        """
        Clona un resultado (que hereda de ResultadoExamenBase) y todos sus
        modelos hijos (related one-to-many).

        Retorna: (cloned_result, n_children_cloned) o (None, 0) si ya existe.
        """
        ModelClass = type(source_resultado)

        # ── Idempotencia: ¿destino ya tiene resultado de este tipo?
        try:
            existing = ModelClass.objects.filter(
                visita_examen=dest_visita_examen
            ).first()
            if existing:
                return None, 0  # ya existe
        except Exception:
            pass

        # ── Construir dict de campos a copiar
        field_values = {}
        for field in ModelClass._meta.fields:
            if field.primary_key:
                continue
            if field.name in ("visita_examen", "visita_examen_id"):
                continue
            # auto_now / auto_now_add se dejan que Django los llene
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue
            field_values[field.attname] = getattr(source_resultado, field.attname)

        new_result = None
        n_children = 0

        if ejecutar:
            new_result = ModelClass(visita_examen=dest_visita_examen, **field_values)
            new_result.save()

            # ── Clonar modelos hijos (one-to-many related objects)
            for rel in ModelClass._meta.related_objects:
                if not rel.one_to_many:
                    continue

                accessor_name = rel.get_accessor_name()
                related_manager = getattr(source_resultado, accessor_name, None)
                if related_manager is None:
                    continue

                ChildModel = rel.related_model
                fk_field_name = rel.field.name  # nombre del FK al padre

                for child in related_manager.all():
                    child_values = {}
                    for f in ChildModel._meta.fields:
                        if f.primary_key:
                            continue
                        if f.name == fk_field_name or f.attname == fk_field_name + "_id":
                            continue
                        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
                            continue
                        child_values[f.attname] = getattr(child, f.attname)

                    new_child = ChildModel(**{fk_field_name: new_result}, **child_values)
                    new_child.save()
                    n_children += 1
        else:
            # dry-run: contar hijos que se copiarían
            for rel in ModelClass._meta.related_objects:
                if not rel.one_to_many:
                    continue
                accessor_name = rel.get_accessor_name()
                related_manager = getattr(source_resultado, accessor_name, None)
                if related_manager is None:
                    continue
                n_children += related_manager.count()

        return new_result, n_children

    # ── Manejo especial de Antecedentes ───────────────────────────────────
    def _handle_antecedentes(self, source_ve, dest_ve, paciente, ejecutar):
        """
        Antecedentes es único por paciente (no se clona el resultado),
        solo se crea el AntecedentesVisitaLink al VisitaExamen destino.
        """
        # Verificar si destino ya tiene link
        if AntecedentesVisitaLink.objects.filter(visita_examen=dest_ve).exists():
            self._log("      ~ AntecedentesVisitaLink ya existe en destino")
            return False

        # Obtener el AntecedentesResult del paciente
        try:
            antecedentes = AntecedentesResult.objects.get(paciente=paciente)
        except AntecedentesResult.DoesNotExist:
            # Si no tiene antecedentes, verificar link del origen
            try:
                source_link = AntecedentesVisitaLink.objects.get(visita_examen=source_ve)
                antecedentes = source_link.antecedentes_result
            except AntecedentesVisitaLink.DoesNotExist:
                self._warn("      ! No hay antecedentes para este paciente")
                return False

        if ejecutar:
            AntecedentesVisitaLink.objects.create(
                visita_examen=dest_ve,
                antecedentes_result=antecedentes,
                fue_revisado=False,
                fue_actualizado=False,
            )

        self._ok("      + AntecedentesVisitaLink creado")
        return True

    # ── Core ──────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        ejecutar = options["ejecutar"]
        modo = "EJECUCION REAL" if ejecutar else "DRY-RUN (sin cambios)"

        self._log("")
        self._log("=" * 65)
        self._log("  Copiar resultados de exámenes Sueño — {}".format(modo))
        self._log("=" * 65)
        self._log("")

        # Validar tipos de visita
        try:
            tipo_origen = TipoVisita.objects.get(id=TIPO_VISITA_ORIGEN_ID)
            tipo_destino = TipoVisita.objects.get(id=TIPO_VISITA_DESTINO_ID)
        except TipoVisita.DoesNotExist as e:
            self._err("  TipoVisita no encontrado: {}".format(e))
            return

        self._log("  Origen  : TV#{} {}".format(tipo_origen.id, tipo_origen.nombre))
        self._log("  Destino : TV#{} {}".format(tipo_destino.id, tipo_destino.nombre))
        self._log("")

        # Pacientes que tienen AMBAS visitas
        pacientes = (
            DatosDemograficos.objects.filter(
                visitas__Tipo_visita=tipo_origen,
            )
            .filter(
                visitas__Tipo_visita=tipo_destino,
            )
            .distinct()
        )

        total_pacientes = pacientes.count()
        self._log("  Pacientes con ambas visitas (TV=7 y TV=20): {}".format(total_pacientes))
        self._log("")

        if total_pacientes == 0:
            self._warn("  No hay pacientes que procesar.")
            return

        # Contadores
        resultados_copiados = 0
        resultados_ya_existentes = 0
        resultados_sin_datos = 0
        antecedentes_links = 0
        hijos_copiados = 0
        examenes_sin_match = 0
        estados_actualizados = 0
        errores = 0

        with transaction.atomic():
            sid = transaction.savepoint()

            for pac in pacientes:
                pac_label = "{} {} (ID={})".format(
                    pac.primer_nombre or "", pac.primer_apellido or "", pac.id
                )
                self._log("  >> {}".format(pac_label))

                # Obtener visita origen y destino
                visita_origen = (
                    Visita.objects.filter(paciente=pac, Tipo_visita=tipo_origen)
                    .prefetch_related("visita_examenes__examen")
                    .first()
                )
                visita_destino = (
                    Visita.objects.filter(paciente=pac, Tipo_visita=tipo_destino)
                    .prefetch_related("visita_examenes__examen")
                    .first()
                )

                if not visita_origen or not visita_destino:
                    self._warn("     ! Falta visita origen o destino, omitido")
                    continue

                # Map: examen_id -> VisitaExamen del origen
                source_map = {}
                for ve in visita_origen.visita_examenes.all():
                    source_map[ve.examen_id] = ve

                # Procesar cada VisitaExamen del destino
                for dest_ve in visita_destino.visita_examenes.select_related("examen").all():
                    examen = dest_ve.examen
                    examen_label = "{} (ID={})".format(examen.nombre, examen.id)

                    source_ve = source_map.get(examen.id)
                    if not source_ve:
                        examenes_sin_match += 1
                        self._log("     - {} : sin equivalente en origen".format(examen_label))
                        continue

                    # ── Caso especial: Antecedentes
                    is_antecedentes = "antecedentes" in examen.nombre.lower()
                    if is_antecedentes:
                        ok = self._handle_antecedentes(source_ve, dest_ve, pac, ejecutar)
                        if ok:
                            antecedentes_links += 1
                        # Actualizar estado del VisitaExamen
                        if source_ve.estado != "pendiente" and dest_ve.estado == "pendiente":
                            if ejecutar:
                                dest_ve.estado = source_ve.estado
                                dest_ve.notas_examinador = source_ve.notas_examinador
                                dest_ve.evaluador = source_ve.evaluador
                                dest_ve.save()
                            estados_actualizados += 1
                        continue

                    # ── Caso general: ResultadoExamenBase
                    try:
                        source_resultado = source_ve.get_resultado_instance()
                    except Exception as e:
                        self._err("     ! Error obteniendo resultado de {}: {}".format(
                            examen_label, e
                        ))
                        errores += 1
                        continue

                    if source_resultado is None:
                        resultados_sin_datos += 1
                        self._log("     - {} : origen sin resultado".format(examen_label))
                        continue

                    # Verificar si destino ya tiene resultado
                    dest_resultado = dest_ve.get_resultado_instance()
                    if dest_resultado is not None:
                        resultados_ya_existentes += 1
                        self._log("     ~ {} : destino ya tiene resultado".format(examen_label))
                        # Aun así actualizar estado
                        if source_ve.estado != "pendiente" and dest_ve.estado == "pendiente":
                            if ejecutar:
                                dest_ve.estado = source_ve.estado
                                dest_ve.notas_examinador = source_ve.notas_examinador
                                dest_ve.evaluador = source_ve.evaluador
                                dest_ve.save()
                            estados_actualizados += 1
                        continue

                    # ── Clonar resultado
                    try:
                        new_result, n_children = self._clone_result(
                            source_resultado, dest_ve, ejecutar
                        )
                        if new_result is not None or not ejecutar:
                            resultados_copiados += 1
                            hijos_copiados += n_children
                            self._ok("     + {} : resultado copiado ({} hijos)".format(
                                examen_label, n_children
                            ))
                        else:
                            resultados_ya_existentes += 1
                            self._log("     ~ {} : ya existe (detectado en clone)".format(
                                examen_label
                            ))
                    except Exception as e:
                        errores += 1
                        self._err("     ! Error clonando {}: {}".format(examen_label, e))
                        continue

                    # Actualizar estado del VisitaExamen
                    if source_ve.estado != "pendiente" and dest_ve.estado == "pendiente":
                        if ejecutar:
                            dest_ve.estado = source_ve.estado
                            dest_ve.notas_examinador = source_ve.notas_examinador
                            dest_ve.evaluador = source_ve.evaluador
                            dest_ve.save()
                        estados_actualizados += 1

            # Dry-run: revertir
            if not ejecutar:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)

        # ── Resumen ───────────────────────────────────────────────────────
        self._log("")
        self._log("=" * 65)
        self._log("  RESUMEN {}".format("(DRY-RUN)" if not ejecutar else "(APLICADO)"))
        self._log("=" * 65)
        self._log("  Pacientes procesados           : {}".format(total_pacientes))
        self._log("  Resultados copiados            : {}".format(resultados_copiados))
        self._log("  Modelos hijos copiados         : {}".format(hijos_copiados))
        self._log("  Ya existentes (omitidos)       : {}".format(resultados_ya_existentes))
        self._log("  Sin datos en origen            : {}".format(resultados_sin_datos))
        self._log("  Sin equivalente en origen      : {}".format(examenes_sin_match))
        self._log("  AntecedentesLinks creados      : {}".format(antecedentes_links))
        self._log("  Estados actualizados           : {}".format(estados_actualizados))
        self._log("  Errores                        : {}".format(errores))
        self._log("")

        if not ejecutar and resultados_copiados > 0:
            self._warn(
                "  Para aplicar estos cambios ejecute:\n"
                "    python manage.py copiar_resultados_sueno --ejecutar\n"
            )
