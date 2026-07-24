# -*- encoding: utf-8 -*-
"""
ModelForms for sleep exam results.

Each form maps to a Result model and excludes the 'visita_examen' FK
(which is set in the view via ExamSaveMixin.save_form).
"""
from django import forms

from ..models import (
    PittsburghResult,
    EpworthResult,
    MEWResult,
    BerlinResult,
    AtenasResult,
    ISIResult,
    StopBangResult,
    SuenoFisicoResult,
    SuenoAnamnesisResult,
)
from ..services.exam_scoring import (
    interpretar_epworth,
    interpretar_psqi,
    interpretar_atenas,
    interpretar_isi,
    cronotipo_mew,
    interpretar_stopbang,
    score_berlin,
)


class PittsburghForm(forms.ModelForm):
    """PSQI: 7 componentes (0–3), total 0–21 e interpretación."""

    HTML_FIELD_MAP = {
        "horas_sueno_real": "horas_dormidas",
    }

    class Meta:
        model = PittsburghResult
        exclude = [
            "visita_examen",
            "puntuacion_total",
            "interpretacion",
            "componente_calidad",
            "componente_latencia",
            "componente_duracion",
            "componente_eficiencia",
            "componente_perturbaciones",
            "componente_medicacion",
            "componente_disfuncion",
        ]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for html_name, model_name in self.HTML_FIELD_MAP.items():
                if html_name in data and model_name not in data:
                    data[model_name] = data[html_name]
        super().__init__(data, *args, **kwargs)

    def map_frecuencia(self, val):
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

    def map_latencia(self, val):
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

    def calcular_horas_cama(self, acostarse, levantarse):
        if not acostarse or not levantarse:
            return 0
        import datetime
        if isinstance(acostarse, str):
            acostarse = datetime.datetime.strptime(acostarse, "%H:%M").time()
        if isinstance(levantarse, str):
            levantarse = datetime.datetime.strptime(levantarse, "%H:%M").time()
        a = datetime.datetime.combine(datetime.date.today(), acostarse)
        l = datetime.datetime.combine(datetime.date.today(), levantarse)
        if l < a:
            l += datetime.timedelta(days=1)
        return (l - a).total_seconds() / 3600

    def clean(self):
        cleaned = super().clean()

        raw_cal = (cleaned.get("calidad_sueno") or "").lower()
        if "muy buena" in raw_cal:
            calidad = 0
        elif "bastante buena" in raw_cal:
            calidad = 1
        elif "bastante mala" in raw_cal:
            calidad = 2
        elif "muy mala" in raw_cal:
            calidad = 3
        else:
            calidad = 0

        lat_base = self.map_latencia(cleaned.get("latencia_sueno"))
        lat_freq = self.map_frecuencia(cleaned.get("conciliar_sueno"))
        lat_total = lat_base + lat_freq
        if lat_total == 0:
            latencia = 0
        elif lat_total <= 2:
            latencia = 1
        elif lat_total <= 4:
            latencia = 2
        else:
            latencia = 3

        horas = float(cleaned.get("horas_dormidas") or 0)
        if horas >= 7:
            duracion = 0
        elif horas >= 6:
            duracion = 1
        elif horas >= 5:
            duracion = 2
        else:
            duracion = 3

        horas_cama = self.calcular_horas_cama(
            cleaned.get("hora_acostarse"),
            cleaned.get("hora_levantarse"),
        )
        eficiencia = (horas / horas_cama * 100) if horas_cama > 0 else 0
        if eficiencia >= 85:
            eficiencia_score = 0
        elif eficiencia >= 75:
            eficiencia_score = 1
        elif eficiencia >= 65:
            eficiencia_score = 2
        else:
            eficiencia_score = 3

        campos = [
            "despertarse_sueno",
            "levantarse_servicio_sueno",
            "respirar",
            "toser_roncar_sueno",
            "sentir_frio_sueno",
            "calor_sueno",
            "pesadillas_sueno",
            "dolores_sueno",
            "otras_sueno",
        ]
        suma_alt = sum(self.map_frecuencia(cleaned.get(c)) for c in campos)
        if suma_alt == 0:
            alteraciones = 0
        elif suma_alt <= 9:
            alteraciones = 1
        elif suma_alt <= 18:
            alteraciones = 2
        else:
            alteraciones = 3

        medicacion = self.map_frecuencia(cleaned.get("medicinas_sueno"))
        somnolencia = self.map_frecuencia(cleaned.get("somnolencia_sueno"))
        animo_l = (cleaned.get("problemas_animos_sueno") or "").lower()
        if "ningun" in animo_l:
            animo_score = 0
        elif "leve" in animo_l or "ligero" in animo_l:
            animo_score = 1
        elif "grave" in animo_l:
            animo_score = 3
        else:
            animo_score = 2
        dis_total = somnolencia + animo_score
        if dis_total == 0:
            disfuncion = 0
        elif dis_total <= 2:
            disfuncion = 1
        elif dis_total <= 4:
            disfuncion = 2
        else:
            disfuncion = 3

        total = (
            calidad + latencia + duracion
            + eficiencia_score + alteraciones
            + medicacion + disfuncion
        )
        cleaned["componente_calidad"] = calidad
        cleaned["componente_latencia"] = latencia
        cleaned["componente_duracion"] = duracion
        cleaned["componente_eficiencia"] = eficiencia_score
        cleaned["componente_perturbaciones"] = alteraciones
        cleaned["componente_medicacion"] = medicacion
        cleaned["componente_disfuncion"] = disfuncion
        cleaned["puntuacion_total"] = total
        cleaned["interpretacion"] = interpretar_psqi(total)
        return cleaned


class EpworthForm(forms.ModelForm):
    class Meta:
        model = EpworthResult
        exclude = ["visita_examen", "interpretacion"]

    HTML_FIELD_MAP = {
        "epworth_leyendo": "sentado_leyendo",
        "epworth_tv": "viendo_tv",
        "epworth_teatro": "sentado_teatro",
        "epworth_pasajero": "pasajero_coche",
        "epworth_tumbado": "tumbado_tarde",
        "epworth_charlando": "charlando",
        "epworth_comida": "despues_comer",
        "epworth_trafico": "trafico",
    }

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for html_name, model_name in self.HTML_FIELD_MAP.items():
                if html_name in data and model_name not in data:
                    data[model_name] = data[html_name]
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        fields = [
            "sentado_leyendo", "viendo_tv", "sentado_teatro", "pasajero_coche",
            "tumbado_tarde", "charlando", "despues_comer", "trafico",
        ]
        total = 0
        for f in fields:
            val = cleaned.get(f)
            if val is not None:
                try:
                    total += int(val)
                except (ValueError, TypeError):
                    pass
        cleaned["puntaje_total"] = total
        cleaned["interpretacion"] = interpretar_epworth(total)
        return cleaned


class MEWForm(forms.ModelForm):
    class Meta:
        model = MEWResult
        exclude = ["visita_examen"]

    HTML_FIELD_MAP = {
        "hora_levantarse_meq": "hora_levantarse",
        "hora_acostarse_meq": "hora_acostarse",
        "uso_despertador_meq": "uso_despertador",
        "facilidad_levantarse_meq": "facilidad_levantarse",
        "alerta_manana_meq": "alerta_manana",
        "apetito_manana_meq": "apetito_manana",
        "descanso_manana_meq": "descanso_manana",
        "hora_acostarse_libre_meq": "hora_acostarse_libre",
        "ejercicio_manana_meq": "ejercicio_manana",
        "ejercicio_fisico_meq": "ejercicio_fisico",
        "hora_cansancio_noche_meq": "hora_cansancio_noche",
        "prueba_mental_meq": "prueba_mental",
        "cansancio_11pm_meq": "cansancio_11pm",
        "despertar_tarde_meq": "despertar_tarde",
        "guardia_nocturna_meq": "guardia_nocturna",
        "trabajo_fisico_meq": "trabajo_fisico",
        "ejercicio_nocturno_meq": "ejercicio_nocturno",
        "horario_trabajo_meq": "horario_trabajo",
        "maximo_bienestar_meq": "maximo_bienestar",
        "tipo_persona_meq": "tipo_persona",
    }

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for html_name, model_name in self.HTML_FIELD_MAP.items():
                if html_name in data and model_name not in data:
                    data[model_name] = data[html_name]
            if "puntuacion" not in data:
                data["puntuacion"] = data.get("puntuacion", "0")
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        try:
            puntuacion = int(cleaned.get("puntuacion", 0) or 0)
        except (ValueError, TypeError):
            puntuacion = 0
        cleaned["tipo_persona"] = cronotipo_mew(puntuacion)
        cleaned["puntuacion"] = puntuacion
        return cleaned


class BerlinForm(forms.ModelForm):
    class Meta:
        model = BerlinResult
        exclude = [
            "visita_examen",
            "categoria1_positiva",
            "categoria2_positiva",
            "categoria3_positiva",
            "categorias_positivas",
            "riesgo",
            "interpretacion",
        ]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for bf in ("somnolencia_conducir", "presion_alta"):
                val = data.get(bf, "")
                if isinstance(val, str):
                    data[bf] = val.lower() in ("true", "1", "on", "si", "sí")
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        cleaned.update(score_berlin(cleaned))
        return cleaned


_ATENAS_PUNTOS = {
    "ningún problema": 0,
    "ninguna": 0,
    "ligeramente retrasado": 1,
    "marcadamente retrasado": 2,
    "muy retrasado o no durmió en absoluto": 3,
    "problema menor": 1,
    "problema considerable": 2,
    "problema serio o no durmió en absoluto": 3,
    "no más temprano": 0,
    "un poco más temprano": 1,
    "marcadamente más temprano": 2,
    "mucho más temprano o no durmió en absoluto": 3,
    "suficiente": 0,
    "ligeramente insuficiente": 1,
    "marcadamente insuficiente": 2,
    "muy insuficiente o no durmió en absoluto": 3,
    "satisfactoria": 0,
    "ligeramente insatisfactoria": 1,
    "marcadamente insatisfactoria": 2,
    "muy insatisfactoria o no durmió en absoluto": 3,
    "normal": 0,
    "leve": 1,
    "considerable": 2,
    "intensa": 3,
}


class AtenasForm(forms.ModelForm):
    class Meta:
        model = AtenasResult
        exclude = ["visita_examen", "interpretacion"]

    def clean(self):
        cleaned = super().clean()
        fields = [
            "induccion_dormir", "despertares_noche", "despertar_temprano",
            "duracion_dormir", "calidad_dormir", "bienestar_dia",
            "funcionamiento_dia", "somnolencia_dia",
        ]
        total = 0
        for f in fields:
            key = (cleaned.get(f) or "").strip().lower().split("(")[0].strip()
            if key in _ATENAS_PUNTOS:
                total += _ATENAS_PUNTOS[key]
            else:
                for token in reversed(key.split()):
                    if token.isdigit():
                        total += int(token)
                        break
        cleaned["puntuacion_total"] = total
        cleaned["interpretacion"] = interpretar_atenas(total)
        return cleaned


_ISI_PUNTOS = {
    "ninguno": 0, "poco": 1, "moderado": 2, "severo": 3, "muy severo": 4,
    "muy satisfecho": 0, "satisfecho": 1, "moderadamente satisfecho": 2,
    "insatisfecho": 3, "muy insatisfecho": 4,
    "no es notable": 0, "un poco notable": 1, "moderadamente notable": 2,
    "muy notable": 3, "demasiado notable": 4,
    "para nada preocupado": 0, "un poco preocupado": 1,
    "moderadamente preocupado": 2, "muy preocupado": 3, "demasiado preocupado": 4,
    "no interfiere": 0, "interfiere un poco": 1, "interfiere moderadamente": 2,
    "interfiere mucho": 3, "interfiere demasiado": 4,
}


class ISIForm(forms.ModelForm):
    class Meta:
        model = ISIResult
        exclude = ["visita_examen", "interpretacion"]

    def clean(self):
        cleaned = super().clean()
        fields = [
            "dificultad_dormir", "dificultad_mantener_sueno", "despertar_temprano",
            "satisfaccion_sueno", "notabilidad_problema", "preocupacion_sueno",
            "interferencia_sueno",
        ]
        total = 0
        for f in fields:
            key = (cleaned.get(f) or "").strip().lower()
            if key in _ISI_PUNTOS:
                total += _ISI_PUNTOS[key]
        cleaned["puntuacion_total"] = total
        cleaned["interpretacion"] = interpretar_isi(total)
        return cleaned


class StopBangForm(forms.ModelForm):
    class Meta:
        model = StopBangResult
        exclude = ["visita_examen"]

    BOOL_FIELDS = [
        "ronca_fuerte", "cansado_frecuencia", "deja_respirar", "presion_arterial",
        "imc_alto", "mayor_50", "cuello_grande", "masculino",
    ]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for bf in self.BOOL_FIELDS:
                val = data.get(bf)
                if val is not None:
                    data[bf] = str(val) in ("1", "true", "True")
            if "riesgo" not in data and data.get("riesgo_osa"):
                data["riesgo"] = data.get("riesgo_osa")
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        campos = [cleaned.get(f, False) for f in self.BOOL_FIELDS]
        puntaje_total = sum(bool(c) for c in campos)
        stop_positivos = sum(bool(c) for c in campos[:4])
        bang_positivos = sum(bool(c) for c in campos[4:])
        alto_alt = stop_positivos >= 2 and bang_positivos >= 2
        scored = interpretar_stopbang(
            puntaje_total, stop_positivos, bang_positivos, alto_alt
        )
        cleaned["puntaje_total"] = puntaje_total
        cleaned["riesgo"] = scored["riesgo"]
        cleaned["stop_positivos"] = stop_positivos
        cleaned["bang_positivos"] = bang_positivos
        cleaned["alto_riesgo_alternativo"] = scored["alto_riesgo_alternativo"]
        return cleaned


class SuenoAnamnesisForm(forms.ModelForm):
    class Meta:
        model = SuenoAnamnesisResult
        exclude = ["visita_examen"]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            periodos = data.getlist("periodo_siestas")
            if periodos:
                data["periodo_siestas"] = "; ".join(v for v in periodos if v)
        super().__init__(data, *args, **kwargs)


class SuenoFisicoForm(forms.ModelForm):
    class Meta:
        model = SuenoFisicoResult
        exclude = ["visita_examen"]

    HTML_FIELD_MAP = {
        "weight": "peso",
        "height": "talla",
        "bmi": "imc",
        "bmi_range": "rango_imc",
        "neck_circumference": "circunferencia_cuello",
        "abdominal_perimeter": "perimetro_abdominal",
        "nostril_symmetry": "simetria_narinas",
        "nostril_type": "tipo_narina",
        "septum_deviation": "desviacion_septo",
        "turbinate_hypertrophy": "hipertrofia_cornetes",
        "grade": "grado",
        "uvula_hypertrophy": "hipertrofia_uvula",
        "biotype": "biotipo",
        "mallampati_score": "mallampati",
        "tonsils": "amigdalas",
        "bite_type": "tipo_mordida",
        "cranial_alteration": "alteracion_craneo",
    }

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for html_name, model_name in self.HTML_FIELD_MAP.items():
                if html_name in data and model_name not in data:
                    data[model_name] = data[html_name]
        super().__init__(data, *args, **kwargs)
