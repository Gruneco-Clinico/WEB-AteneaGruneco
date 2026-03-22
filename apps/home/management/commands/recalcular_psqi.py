from django.core.management.base import BaseCommand
from django.db import transaction
from apps.home.models.results_sleep import PittsburghResult
import datetime


class Command(BaseCommand):
    help = "Recalcula todos los puntajes PSQI históricos"

    def handle(self, *args, **kwargs):

        total = 0
        actualizados = 0
        errores = 0

        def to_time(val):
            if isinstance(val, datetime.time):
                return val
            if isinstance(val, str):
                try:
                    return datetime.datetime.strptime(val, "%H:%M").time()
                except:
                    return None
            return None

        def map_freq(val):
            if not val:
                return 0
            val = val.lower()
            if "ninguna" in val:
                return 0
            if "menos" in val:
                return 1
            if "una o dos" in val:
                return 2
            if "tres" in val:
                return 3
            return 0

        def map_calidad(val):
            if not val:
                return 0
            val = val.lower()
            if "bastante buena" in val:
                return 0
            if "buena" in val:
                return 1
            if "mala" in val:
                return 2
            if "bastante mala" in val:
                return 3
            return 0

        def map_latencia(val):
            if not val:
                return 0
            if "0" in val:
                return 0
            if "1" in val:
                return 1
            if "2" in val:
                return 2
            if "3" in val:
                return 3
            return 0

        qs = PittsburghResult.objects.all()

        self.stdout.write(f"Procesando {qs.count()} registros...")

        with transaction.atomic():

            for obj in qs:
                total += 1

                try:
                    # 🕒 tiempos
                    acostarse = to_time(obj.hora_acostarse)
                    levantarse = to_time(obj.hora_levantarse)

                    horas_cama = 0
                    if acostarse and levantarse:
                        a = datetime.datetime.combine(datetime.date.today(), acostarse)
                        l = datetime.datetime.combine(datetime.date.today(), levantarse)

                        if l < a:
                            l += datetime.timedelta(days=1)

                        horas_cama = (l - a).total_seconds() / 3600

                    # 🧠 componentes
                    calidad = map_calidad(obj.calidad_sueno)

                    lat_base = map_latencia(obj.latencia_sueno)
                    lat_freq = map_freq(obj.conciliar_sueno)

                    lat_total = lat_base + lat_freq
                    latencia = 0 if lat_total == 0 else 1 if lat_total <= 2 else 2 if lat_total <= 4 else 3

                    horas = float(obj.horas_dormidas or 0)

                    duracion = 0 if horas >= 7 else 1 if horas >= 6 else 2 if horas >= 5 else 3

                    eficiencia = (horas / horas_cama * 100) if horas_cama > 0 else 0
                    eficiencia_score = 0 if eficiencia >= 85 else 1 if eficiencia >= 75 else 2 if eficiencia >= 65 else 3

                    campos = [
                        obj.despertarse_sueno,
                        obj.levantarse_servicio_sueno,
                        obj.respirar,
                        obj.toser_roncar_sueno,
                        obj.sentir_frio_sueno,
                        obj.calor_sueno,
                        obj.pesadillas_sueno,
                        obj.dolores_sueno,
                        obj.otras_sueno,
                    ]

                    suma_alt = sum(map_freq(c) for c in campos)

                    alteraciones = 0 if suma_alt == 0 else 1 if suma_alt <= 9 else 2 if suma_alt <= 18 else 3

                    medicacion = map_freq(obj.medicinas_sueno)

                    somnolencia = map_freq(obj.somnolencia_sueno)

                    animo = (obj.problemas_animos_sueno or "").lower()
                    if "ningun" in animo:
                        animo_score = 0
                    elif "leve" in animo:
                        animo_score = 1
                    elif "grave" in animo:
                        animo_score = 3
                    else:
                        animo_score = 2

                    dis_total = somnolencia + animo_score
                    disfuncion = 0 if dis_total == 0 else 1 if dis_total <= 2 else 2 if dis_total <= 4 else 3

                    # 🎯 TOTAL
                    total_score = (
                        calidad + latencia + duracion +
                        eficiencia_score + alteraciones +
                        medicacion + disfuncion
                    )

                    obj.puntuacion_total = total_score


                    obj.save()
                    actualizados += 1

                except Exception as e:
                    errores += 1
                    self.stdout.write(self.style.ERROR(f"Error ID {obj.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n✔ Total: {total} | ✔ Actualizados: {actualizados} | ❌ Errores: {errores}"
        ))