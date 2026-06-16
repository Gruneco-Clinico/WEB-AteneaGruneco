"""
Management command: migrar_pacientes_sueno

Migra pacientes del Proyecto Sueno (TipoVisita ID=7) al Proyecto
Caracterizacion Sueno (TipoVisita ID=20).

Operacion segura e idempotente:
  - No elimina datos del proyecto origen.
  - No duplica relaciones M2M ni visitas.
  - Puede ejecutarse multiples veces sin efectos secundarios.

Uso:
  python manage.py migrar_pacientes_sueno            # solo muestra lo que haria
  python manage.py migrar_pacientes_sueno --ejecutar  # aplica cambios reales
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.home.models import (
    DatosDemograficos,
    Proyecto,
    TipoVisita,
    Visita,
    VisitaExamen,
    Examen,
)


# ── Configuracion de origen / destino ────────────────────────────────────
TIPO_VISITA_ORIGEN_ID = 7
TIPO_VISITA_DESTINO_ID = 20
NOMBRE_VISITA_NUEVA = "Caracterizacion Sueno"


class Command(BaseCommand):
    help = (
        "Migra pacientes con visitas TipoVisita ID=7 al proyecto destino "
        "(TipoVisita ID=20). Operacion idempotente y segura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--ejecutar",
            action="store_true",
            default=False,
            help="Aplica los cambios realmente. Sin esta flag solo se muestra un reporte (dry-run).",
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

    # ── Validacion ────────────────────────────────────────────────────────
    def _validar_entidades(self):
        """Retorna (tipo_origen, tipo_destino, proyecto_destino) o levanta."""
        try:
            tipo_origen = TipoVisita.objects.select_related("proyecto").get(
                id=TIPO_VISITA_ORIGEN_ID
            )
        except TipoVisita.DoesNotExist:
            self._err(f"TipoVisita origen (ID={TIPO_VISITA_ORIGEN_ID}) no existe.")
            return None

        try:
            tipo_destino = TipoVisita.objects.select_related("proyecto").get(
                id=TIPO_VISITA_DESTINO_ID
            )
        except TipoVisita.DoesNotExist:
            self._err(f"TipoVisita destino (ID={TIPO_VISITA_DESTINO_ID}) no existe.")
            return None

        proyecto_destino = tipo_destino.proyecto
        if not proyecto_destino:
            self._err("El TipoVisita destino no tiene un Proyecto asociado.")
            return None

        self._log(f"  Origen  : TipoVisita #{tipo_origen.id} \"{tipo_origen.nombre}\" "
                   f"(Proyecto: \"{tipo_origen.proyecto.nombre if tipo_origen.proyecto else 'N/A'}\")")
        self._log(f"  Destino : TipoVisita #{tipo_destino.id} \"{tipo_destino.nombre}\" "
                   f"(Proyecto: \"{proyecto_destino.nombre}\")")

        return tipo_origen, tipo_destino, proyecto_destino

    # ── Core ──────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        ejecutar = options["ejecutar"]
        modo = "EJECUCION REAL" if ejecutar else "DRY-RUN (sin cambios)"

        self._log("")
        self._log(f"{'='*60}")
        self._log(f"  Migracion de pacientes Sueno — {modo}")
        self._log(f"{'='*60}")
        self._log("")

        resultado = self._validar_entidades()
        if resultado is None:
            return
        tipo_origen, tipo_destino, proyecto_destino = resultado

        # 1. Obtener pacientes candidatos: vinculados al proyecto origen
        #    Y que tengan al menos una visita con tipo_visita = origen.
        pacientes_con_visita_origen = (
            DatosDemograficos.objects.filter(
                visitas__Tipo_visita=tipo_origen,
            )
            .distinct()
        )

        total = pacientes_con_visita_origen.count()
        self._log(f"\n  Pacientes con visita TipoVisita #{tipo_origen.id}: {total}\n")

        if total == 0:
            self._warn("  No hay pacientes que migrar.")
            return

        # Contadores
        pacientes_vinculados = 0
        pacientes_ya_en_destino = 0
        visitas_creadas = 0
        visitas_ya_existentes = 0
        examenes_asociados = 0
        errores = 0

        # Examenes que deben crearse en la nueva visita (tomados del tipo destino)
        examenes_destino = []
        if tipo_destino.examenes:
            for ex_data in tipo_destino.examenes:
                try:
                    examenes_destino.append(int(ex_data["id"]))
                except (KeyError, TypeError, ValueError):
                    continue

        self._log(f"  Examenes configurados en TipoVisita destino: {len(examenes_destino)}")
        self._log("")

        with transaction.atomic():
            sid = transaction.savepoint()

            for pac in pacientes_con_visita_origen:
                pac_label = f"[{pac.numero_documento}] {pac.primer_nombre} {pac.primer_apellido}"

                try:
                    # ── 2a. Vincular al proyecto destino (M2M) ────────────
                    ya_vinculado = proyecto_destino.pacientes.filter(id=pac.id).exists()
                    if ya_vinculado:
                        pacientes_ya_en_destino += 1
                        self._log(f"  ~ {pac_label} — ya vinculado al proyecto destino")
                    else:
                        if ejecutar:
                            proyecto_destino.pacientes.add(pac)
                        pacientes_vinculados += 1
                        self._ok(f"  + {pac_label} — vinculado al proyecto destino")

                    # ── 2b. Crear visita con tipo destino si no existe ────
                    visita_destino_existe = Visita.objects.filter(
                        paciente=pac,
                        Tipo_visita=tipo_destino,
                    ).exists()

                    if visita_destino_existe:
                        visitas_ya_existentes += 1
                        self._log(f"    ~ Visita TipoVisita #{tipo_destino.id} ya existe")
                    else:
                        if ejecutar:
                            nueva_visita = Visita.objects.create(
                                paciente=pac,
                                nombre=NOMBRE_VISITA_NUEVA,
                                Tipo_visita=tipo_destino,
                                fecha=timezone.now().date(),
                            )

                            # Crear VisitaExamen para cada examen configurado
                            for examen_id in examenes_destino:
                                try:
                                    examen = Examen.objects.get(id=examen_id)
                                    VisitaExamen.objects.create(
                                        visita=nueva_visita,
                                        examen=examen,
                                        estado="pendiente",
                                    )
                                    examenes_asociados += 1
                                except Examen.DoesNotExist:
                                    self._warn(f"    ! Examen ID={examen_id} no existe, omitido")
                        else:
                            examenes_asociados += len(examenes_destino)

                        visitas_creadas += 1
                        self._ok(f"    + Visita '{NOMBRE_VISITA_NUEVA}' creada")

                except Exception as e:
                    errores += 1
                    self._err(f"  ✗ Error procesando {pac_label}: {e}")
                    continue

            # Si es dry-run, revertir todo
            if not ejecutar:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)

        # ── Resumen ───────────────────────────────────────────────────────
        self._log(f"\n{'='*60}")
        self._log(f"  RESUMEN {'(DRY-RUN)' if not ejecutar else '(APLICADO)'}")
        self._log(f"{'='*60}")
        self._log(f"  Pacientes encontrados          : {total}")
        self._log(f"  Pacientes vinculados (nuevos)   : {pacientes_vinculados}")
        self._log(f"  Pacientes ya en destino         : {pacientes_ya_en_destino}")
        self._log(f"  Visitas creadas                 : {visitas_creadas}")
        self._log(f"  Visitas ya existentes           : {visitas_ya_existentes}")
        self._log(f"  Examenes asociados              : {examenes_asociados}")
        self._log(f"  Errores                         : {errores}")
        self._log("")

        if not ejecutar and (pacientes_vinculados > 0 or visitas_creadas > 0):
            self._warn(
                "  Para aplicar estos cambios ejecute:\n"
                "    python manage.py migrar_pacientes_sueno --ejecutar\n"
            )
