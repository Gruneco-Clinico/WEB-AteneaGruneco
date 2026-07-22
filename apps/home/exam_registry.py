# -*- encoding: utf-8 -*-
"""
Centralized Exam Registry — Single source of truth for all exam type configurations.

Replaces the duplicated mapping dicts in exams_dispatch.py (exam_config),
visit.py (get_url_realizar/ver/editar, possible_related_names).

No model imports at module level to avoid circular imports.
Use get_exam_model() for lazy model resolution.
"""

# Exam ID → configuration. Keys match the Examen.id in the database.
# Missing ID 6 — does not exist in the system.
EXAM_REGISTRY = {
    3: {
        "model_name": "ExamenFisicoResult",
        "template": "examenes_general/General_ExamenFísico.html",
        "related_name": "examenfisicoresult_resultado",
    },
    4: {
        "model_name": "RevisionSistemasResult",
        "template": "examenes_general/General_RevisiónSistemas.html",
        "related_name": "revisionsistemasresult_resultado",
    },
    5: {
        "model_name": "AntecedentesResult",
        "template": "examenes_general/General_Antecedentes.html",
        "related_name": None,  # Uses AntecedentesVisitaLink bridge
        "use_bridge": True,
        "export": {
            "tables": [
                {
                    "related_name": "antecedentes_patologicos",
                    "label": "Antecedentes patológicos",
                    "columns": (
                        "tipo_patologia",
                        "fecha_inicio",
                        "ha_recibido_tratamiento",
                        "detalle_tratamiento",
                        "tiene_complicaciones",
                        "activo",
                        "observaciones",
                    ),
                },
            ],
        },
    },
    7: {
        "model_name": "AnalisisGeneralResult",
        "template": "examenes_general/General_Análisis.html",
        "related_name": "analisisgeneralresult_resultado",
    },
    8: {
        "model_name": "MedicamentosResult",
        "template": "examenes_general/General_Medicamentos.html",
        "related_name": "medicamentosresult_resultado",
        "export": {
            "tables": [
                {
                    "related_name": "medicamentos",
                    "label": "Medicamentos",
                    "columns": (
                        "nombre_comercial",
                        "nombre_generico",
                        "concentracion",
                        "cantidad",
                        "frecuencia",
                        "via_administracion",
                    ),
                },
            ],
        },
    },
    9: {
        "model_name": "ExamenNeurologicoResult",
        "template": "examenes_general/General_ExamenNeurológico.html",
        "related_name": "examenneurologicoresult_resultado",
    },
    10: {
        "model_name": "SuenoAnamnesisResult",
        "template": "examenes_sueno/Sueno_anamnesis.html",
        "related_name": "suenoanamnesisresult_resultado",
    },
    11: {
        "model_name": None,
        "template": "examenes_sueno/Sueño_Cuestionarios.html",
        "related_name": None,
    },
    12: {
        "model_name": "SuenoFisicoResult",
        "template": "examenes_sueno/Sueño_ExamenFisico.html",
        "related_name": "suenofisicoresult_resultado",
    },
    13: {
        "model_name": "PittsburghResult",
        "template": "examenes_sueno/sueno_Pitsburg.html",
        "related_name": "pittsburghresult_resultado",
    },
    14: {
        "model_name": "EpworthResult",
        "template": "examenes_sueno/sueno_Epworth.html",
        "related_name": "epworthresult_resultado",
    },
    15: {
        "model_name": "StopBangResult",
        "template": "examenes_sueno/sueno_Stop_Bang.html",
        "related_name": "stopbangresult_resultado",
    },
    16: {
        "model_name": "MEWResult",
        "template": "examenes_sueno/sueno_MEW.html",
        "related_name": "mewresult_resultado",
        "export": {
            "summary_fields": ["puntuacion", "tipo_persona"],
        },
    },
    17: {
        "model_name": "BerlinResult",
        "template": "examenes_sueno/sueno_Berlín.html",
        "related_name": "berlinresult_resultado",
    },
    18: {
        "model_name": "AtenasResult",
        "template": "examenes_sueno/sueno_atenas.html",
        "related_name": "atenasresult_resultado",
    },
    19: {
        "model_name": "ISIResult",
        "template": "examenes_sueno/sueno_ISI.html",
        "related_name": "isiresult_resultado",
    },
    20: {
        "model_name": "CognitivoAnamnesisResult",
        "template": "examenes_general/cognitivo_Anamnesis.html",
        "related_name": "cognitivo_anamnesis_resultado",  # Custom related_name
    },
    21: {
        "model_name": "EuroQol5D5LResult",
        "template": "examenes_anosognosia/Anosognosia_Participante_EuroQoL.html",
        "related_name": "euroqol5d5lresult_resultado",
    },
    22: {
        "model_name": "EuroQolEVASaludResult",
        "template": "examenes_anosognosia/Anosognosia_Participante_EVA_EuroQoL.html",
        "related_name": "euroqolevasaludresult_resultado",
    },
    23: {
        "model_name": "ParticipanteYesavageResult",
        "template": "examenes_anosognosia/Anosognosia_Participante_Yesavage.html",
        "related_name": "participanteyesavageresult_resultado",
    },
    24: {
        "model_name": "CuidadorNPIResult",
        "template": "examenes_anosognosia/Anosognosia_Cuidador_NPI.html",
        "related_name": "cuidadornpiresult_resultado",
    },
    25: {
        "model_name": "LawtonBrodyResult",
        "template": "examenes_anosognosia/Anosognosia_Cuidador_LawtonBrody.html",
        "related_name": "lawtonbrodyresult_resultado",
    },
    26: {
        "model_name": "BettyFerrelResult",
        "template": "examenes_anosognosia/Anosognosia_Cuidador_CalidadVida_BettyFerrel.html",
        "related_name": "bettyferrelresult_resultado",
    },
    27: {
        "model_name": "MoCAResult",
        "template": "examenes_anosognosia/Anosognosia_Participante_MoCA.html",
        "related_name": "mocaresult_resultado",
    },
    28: {
        "model_name": "AdherenciaTerapeuticaResult",
        "template": "examenes_anosognosia/Anosognosia_Participante_AdherenciaTerapeutica.html",
        "related_name": "adherenciaterapeuticaresult_resultado",
    },
    29: {
        "model_name": "ZaritResult",
        "template": "examenes_anosognosia/Anosognosia_Cuidador_EscalaZarit.html",
        "related_name": "zaritresult_resultado",
    },
    30: {
        "model_name": "AQDCuidadorResult",
        "template": "examenes_anosognosia/Anosognosia_Cuidador_AQD.html",
        "related_name": "aqdcuidadorresult_resultado",
    },
    31: {
        "model_name": "AQDParticipanteResult",
        "template": "examenes_anosognosia/Anosognosia_Participante_AQD.html",
        "related_name": "aqdparticipanteresult_resultado",
    },
    32: {
        "model_name": "RedLatSpanishResult",
        "template": "examenes_anosognosia/Anosognosia_Cuidador_RedLatSpanish.html",
        "related_name": "redlatspanishresult_resultado",
        "export": {
            "summary_fields": [
                "puntaje_total",
                "puntaje_autocuidado",
                "puntaje_cuidado_hogar",
                "puntaje_trabajo_recreacion",
                "puntaje_compras_dinero",
                "puntaje_viajes",
                "puntaje_comunicacion",
                "puntaje_tecnologia",
            ],
        },
    },
    33: {
        "model_name": "CDRCuidadorResult",
        "template": "examenes_anosognosia/Anosognosia_Cuidador_CDR.html",
        "related_name": "cdrcuidadorresult_resultado",
    },
    34: {
        "model_name": "CDRParticipanteResult",
        "template": "examenes_anosognosia/Anosognosia_Participante_CDR.html",
        "related_name": "cdrparticipanteresult_resultado",
    },
    35: {
        "model_name": "PuntajeCDRResult",
        "template": "examenes_anosognosia/CDR_Evaluacion_Clinica.html",
        "related_name": "puntajecdrresult_resultado",
        "export": {
            "summary_fields": ["cdr_global", "suma_cajas", "cdr_interpretacion"],
        },
    },
    36: {
        "model_name": "ConsentimientoInformadoParticipanteResult",
        "template": "examenes_anosognosia/Consentimiento_Informado_Participante.html",
        "related_name": "consentimientoinformadoparticipanteresult_resultado",
    },
    37: {
        "model_name": "ConsentimientoInformadoCuidadorResult",
        "template": "examenes_anosognosia/Consentimiento_Informado_Cuidador.html",
        "related_name": "consentimientoinformadocuidadorresult_resultado",
    },
    38: {
        "model_name": "AnamnesisCuidadorResult",
        "template": "examenes_anosognosia/Anamnesis_Cuidador_ANG.html",
        "related_name": "anamnesiscuidadorresult_resultado",
    },
    39: {
        "model_name": "AnamnesisParticipanteResult",
        "template": "examenes_anosognosia/Anamnesis_Participante_ANG.html",
        "related_name": "anamnesisparticipanteresult_resultado",
    },
    40: {
        "model_name": "SeguimientoIntervencionesResult",
        "template": "examenes_anosognosia/SeguimientoIntervenciones_ANG.html",
        "related_name": "seguimientointervencionesresult_resultado",
    },
}

# All valid exam IDs (sorted for deterministic iteration)
ALL_EXAM_IDS = sorted(EXAM_REGISTRY.keys())


def get_exam_config(exam_id):
    """Return the config dict for a given exam ID, or None if not found."""
    return EXAM_REGISTRY.get(int(exam_id))


def get_exam_model(exam_id):
    """Lazily resolve and return the Django model class for an exam ID.
    Returns None if the exam has no model (e.g., Cuestionarios ID 11).
    """
    config = get_exam_config(exam_id)
    if not config or not config.get("model_name"):
        return None
    from django.apps import apps
    return apps.get_model("home", config["model_name"])


def get_all_related_names():
    """Return list of all related_names for result instance lookups.
    Excludes exams with no related_name (Antecedentes, Cuestionarios).
    Order preserved from EXAM_REGISTRY key order.
    """
    return [
        v["related_name"]
        for v in EXAM_REGISTRY.values()
        if v.get("related_name")
    ]
