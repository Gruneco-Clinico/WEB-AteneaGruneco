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


class PittsburghForm(forms.ModelForm):
    """
    Formulario PSQI (Pittsburgh Sleep Quality Index)
    - Calcula automáticamente los 7 componentes (0–3)
    - Calcula puntuación total (0–21)
    - Genera interpretación clínica
    """

    HTML_FIELD_MAP = {
        "horas_sueno_real": "horas_dormidas",
    }

    class Meta:
        model = PittsburghResult
        exclude = [
            "visita_examen",
            "puntuacion_total",
            "interpretacion",
        ]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for html_name, model_name in self.HTML_FIELD_MAP.items():
                if html_name in data and model_name not in data:
                    data[model_name] = data[html_name]
        super().__init__(data, *args, **kwargs)

    # 🔧 Helpers
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

    def map_calidad(self, val):
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

        # 🔥 convertir string → time si es necesario
        if isinstance(acostarse, str):
            acostarse = datetime.datetime.strptime(acostarse, "%H:%M").time()

        if isinstance(levantarse, str):
            levantarse = datetime.datetime.strptime(levantarse, "%H:%M").time()

        a = datetime.datetime.combine(datetime.date.today(), acostarse)
        l = datetime.datetime.combine(datetime.date.today(), levantarse)

        if l < a:
            l += datetime.timedelta(days=1)

        return (l - a).total_seconds() / 3600

    # 🧠 CORE CLÍNICO
    def clean(self):
        cleaned = super().clean()

        # 1️⃣ Calidad subjetiva
        calidad = self.map_calidad(cleaned.get("calidad_sueno"))

        # 2️⃣ Latencia
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

        # 3️⃣ Duración
        horas = float(cleaned.get("horas_dormidas") or 0)

        if horas >= 7:
            duracion = 0
        elif horas >= 6:
            duracion = 1
        elif horas >= 5:
            duracion = 2
        else:
            duracion = 3

        # 4️⃣ Eficiencia
        horas_cama = self.calcular_horas_cama(
            cleaned.get("hora_acostarse"),
            cleaned.get("hora_levantarse")
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

        # 5️⃣ Alteraciones
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

        # 6️⃣ Medicación
        medicacion = self.map_frecuencia(cleaned.get("medicinas_sueno"))

        # 7️⃣ Disfunción diurna
        somnolencia = self.map_frecuencia(cleaned.get("somnolencia_sueno"))

        animo = cleaned.get("problemas_animos_sueno", "")
        if "ningun" in animo.lower():
            animo_score = 0
        elif "leve" in animo.lower():
            animo_score = 1
        elif "grave" in animo.lower():
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

        # 🎯 TOTAL FINAL
        total = (
            calidad + latencia + duracion +
            eficiencia_score + alteraciones +
            medicacion + disfuncion
        )

        cleaned["puntuacion_total"] = total

       
        return cleaned


class EpworthForm(forms.ModelForm):
    """
    The HTML form sends fields with 'epworth_*' prefixed names.
    This form accepts both the model field names and the HTML names.
    """

    class Meta:
        model = EpworthResult
        exclude = ["visita_examen"]

    # HTML field name → model field name mapping
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
            data = data.copy()  # make mutable
            for html_name, model_name in self.HTML_FIELD_MAP.items():
                if html_name in data and model_name not in data:
                    data[model_name] = data[html_name]
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        # Calculate puntaje_total from the 8 response fields
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
        return cleaned


class MEWForm(forms.ModelForm):
    """
    Accepts HTML field names with '_meq' suffix and maps them to model fields.
    Scoring: puntuacion comes from frontend but we validate and derive cronotipo.
    """

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
            # Map 'puntuacion' from POST (may come as 'puntuacion')
            if "puntuacion" not in data:
                data["puntuacion"] = data.get("puntuacion", "0")
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        # Derive cronotipo if tipo_persona not explicitly set
        puntuacion = cleaned.get("puntuacion", 0)
        try:
            puntuacion = int(puntuacion)
        except (ValueError, TypeError):
            puntuacion = 0

        if not cleaned.get("tipo_persona"):
            if puntuacion >= 70:
                cleaned["tipo_persona"] = "Definitivamente matutino"
            elif puntuacion >= 59:
                cleaned["tipo_persona"] = "Moderadamente matutino"
            elif puntuacion >= 42:
                cleaned["tipo_persona"] = "Ni matutino ni vespertino"
            elif puntuacion >= 31:
                cleaned["tipo_persona"] = "Moderadamente vespertino"
            else:
                cleaned["tipo_persona"] = "Definitivamente vespertino"

        cleaned["puntuacion"] = puntuacion
        return cleaned


class BerlinForm(forms.ModelForm):
    """Radio buttons send 'True'/'False' strings for boolean fields."""

    class Meta:
        model = BerlinResult
        exclude = ["visita_examen"]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for bf in ("somnolencia_conducir", "presion_alta"):
                val = data.get(bf, "")
                if isinstance(val, str):
                    data[bf] = val.lower() in ("true", "1", "on", "si", "sí")
        super().__init__(data, *args, **kwargs)


class AtenasForm(forms.ModelForm):
    class Meta:
        model = AtenasResult
        exclude = ["visita_examen"]


class ISIForm(forms.ModelForm):
    class Meta:
        model = ISIResult
        exclude = ["visita_examen"]


class StopBangForm(forms.ModelForm):
    """
    StopBang uses boolean fields but the HTML sends "0"/"1" strings.
    This form coerces them and computes scoring.
    """

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
                    # Convert "1"/"true" → "True" for BooleanField processing
                    data[bf] = str(val) in ("1", "true", "True")
        super().__init__(data, *args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        campos = [cleaned.get(f, False) for f in self.BOOL_FIELDS]
        puntaje_total = sum(bool(c) for c in campos)

        stop_positivos = sum(bool(c) for c in campos[:4])
        bang_positivos = sum(bool(c) for c in campos[4:])

        if puntaje_total <= 2:
            riesgo = "Bajo"
        elif puntaje_total <= 4:
            riesgo = "Intermedio"
        else:
            riesgo = "Alto"

        cleaned["puntaje_total"] = puntaje_total
        cleaned["riesgo"] = riesgo
        cleaned["stop_positivos"] = stop_positivos
        cleaned["bang_positivos"] = bang_positivos
        cleaned["alto_riesgo_alternativo"] = stop_positivos >= 2 and bang_positivos >= 2
        return cleaned


class SuenoAnamnesisForm(forms.ModelForm):
    """
    Handles the parent SuenoAnamnesisResult model only.
    The 8 child model types (TipoQuejaSueno, SustanciaSueno, MedicamentoSueno,
    PantallaSueno, ActividadEnCamaSueno, ActividadFisicaSueno, SintomaSueno,
    SintomaDiurnoSueno) are handled in the view via getlist.
    """

    class Meta:
        model = SuenoAnamnesisResult
        exclude = ["visita_examen"]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            # periodo_siestas is sent as multiple checkboxes; join them
            periodos = data.getlist("periodo_siestas")
            if periodos:
                data["periodo_siestas"] = "; ".join(v for v in periodos if v)
        super().__init__(data, *args, **kwargs)


class SuenoFisicoForm(forms.ModelForm):
    """
    The HTML form sends some fields with English names as fallback.
    This form normalizes them.
    """

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
