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
    """HTML sends 'horas_sueno_real' but model field is 'horas_dormidas'."""

    HTML_FIELD_MAP = {
        "horas_sueno_real": "horas_dormidas",
    }

    class Meta:
        model = PittsburghResult
        exclude = ["visita_examen"]

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            for html_name, model_name in self.HTML_FIELD_MAP.items():
                if html_name in data and model_name not in data:
                    data[model_name] = data[html_name]
        super().__init__(data, *args, **kwargs)


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
