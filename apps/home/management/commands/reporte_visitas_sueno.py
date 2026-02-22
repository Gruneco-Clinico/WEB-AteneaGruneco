"""
Management command: reporte_visitas_sueno
-----------------------------------------
Muestra qué tipos de visita tienen los pacientes que pertenecen
al proyecto "Sueño" (o cualquier proyecto cuyo nombre contenga 'sue').

Uso:
    python manage.py reporte_visitas_sueno
"""

from collections import Counter
from django.core.management.base import BaseCommand
from apps.home.models import Proyecto, Visita


class Command(BaseCommand):
    help = "Lista los tipos de visita de los pacientes del Proyecto Sueño"

    def handle(self, *args, **options):
        proyecto = (
            Proyecto.objects.filter(nombre__icontains="sueno").first()
            or Proyecto.objects.filter(nombre__icontains="sue").first()
        )
        if not proyecto:
            self.stderr.write("No se encontró el proyecto Sueño.")
            return

        pacientes = proyecto.pacientes.all()
        self.stdout.write("Proyecto: {} (ID={})".format(proyecto.nombre, proyecto.id))
        self.stdout.write("Pacientes en proyecto: {}".format(pacientes.count()))
        self.stdout.write("")

        visitas = (
            Visita.objects.filter(paciente__in=pacientes)
            .select_related("Tipo_visita", "Tipo_visita__proyecto")
        )

        counter = Counter()
        for v in visitas:
            tv = v.Tipo_visita
            if tv:
                proy_nombre = tv.proyecto.nombre if tv.proyecto else "Sin proyecto"
                key = (tv.id, tv.nombre, proy_nombre)
            else:
                key = (0, "Sin TipoVisita", "-")
            counter[key] += 1

        header = "{:<6} {:<40} {:<30} {:>8}".format(
            "ID", "TipoVisita", "Proyecto", "Visitas"
        )
        sep = "-" * 90
        self.stdout.write(header)
        self.stdout.write(sep)

        for (tid, tnombre, pnombre), cnt in sorted(
            counter.items(), key=lambda x: -(x[1])
        ):
            self.stdout.write(
                "{:<6} {:<40} {:<30} {:>8}".format(tid, tnombre, pnombre, cnt)
            )

        self.stdout.write(sep)
        self.stdout.write("Total visitas: {}".format(visitas.count()))

        # Detalle por paciente
        self.stdout.write("")
        self.stdout.write("=" * 90)
        self.stdout.write("DETALLE POR PACIENTE")
        self.stdout.write("=" * 90)

        for pac in pacientes.order_by("Primer_nombre"):
            vis_pac = visitas.filter(paciente=pac)
            if not vis_pac.exists():
                continue
            nombre = "{} {}".format(pac.Primer_nombre or "", pac.Primer_apellido or "").strip()
            self.stdout.write("")
            self.stdout.write(">> {} (ID={})".format(nombre, pac.id))
            for v in vis_pac:
                tv = v.Tipo_visita
                tv_info = "{} (ID={})".format(tv.nombre, tv.id) if tv else "Sin tipo"
                fecha = str(v.fecha) if hasattr(v, "fecha") and v.fecha else "sin fecha"
                self.stdout.write("   - {} | {}".format(tv_info, fecha))
