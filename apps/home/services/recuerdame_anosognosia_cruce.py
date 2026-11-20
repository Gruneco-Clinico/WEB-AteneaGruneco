# -*- encoding: utf-8 -*-
"""
Cruce Atenea × PostHog × RecuérdaMe (actividad autenticada) para Anosognosia
(examen form builder 56).

Une las sesiones clínicas (``Interv_fecha`` + correo/documento del paciente) con:

- Biomarcadores PostHog (match por correo).
- Personas activas ese día (serie DAU PostHog).
- Cuenta RecuérdaMe + login_logs + sessionGame vía
  ``POST /v1/integrations/atenea/activity``.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apps.home.models.exam_builder import ExamenSubmission

from . import recuerdame_activity_api, recuerdame_analytics

logger = logging.getLogger(__name__)

EXAMEN_ANOSOGNOSIA_ID = 56
ZONA = ZoneInfo("America/Bogota")
ANIO_MINIMO = 2025

COLUMNAS_CSV = [
    ("paciente_id", "ID paciente"),
    ("documento", "Documento"),
    ("nombre", "Nombre"),
    ("correo", "Correo"),
    ("visita_examen_id", "ID visita examen"),
    ("sesion_no", "Nº sesión"),
    ("fecha", "Fecha intervención"),
    ("hora_inicio", "Hora inicio"),
    ("hora_final", "Hora final"),
    ("asistencia", "Asistencia"),
    ("asistio", "Asistió"),
    ("nivel_participacion", "Nivel de participación"),
    ("destreza", "Destreza"),
    ("estado_participante", "Estado del participante"),
    ("tematica", "Temática"),
    ("observaciones", "Observaciones"),
    ("match_posthog", "Match PostHog"),
    ("person_id", "ID persona PostHog"),
    ("adherencia_pct", "Adherencia PostHog (%)"),
    ("sesiones_posthog", "Sesiones PostHog"),
    ("pageviews_posthog", "Vistas PostHog"),
    ("duracion_media_sesion_seg", "Duración media sesión PostHog (s)"),
    ("amplitud_secciones", "Amplitud secciones"),
    ("rol_aproximado", "Rol aproximado"),
    ("dispositivo_principal", "Dispositivo principal"),
    ("primera_actividad", "Primera actividad PostHog"),
    ("ultima_actividad", "Última actividad PostHog"),
    ("personas_activas_dia", "Personas activas RecuérdaMe ese día"),
    ("match_recuerdame", "Match cuenta RecuérdaMe"),
    ("mongo_id", "ID Mongo RecuérdaMe"),
    ("logins_en_ventana", "Logins en ventana"),
    ("dias_con_login", "Días con login"),
    ("sesiones_juego", "Sesiones de juego"),
    ("login_ese_dia", "Login ese día"),
]


def _como_dict(answers):
    if answers is None:
        return {}
    if isinstance(answers, str):
        try:
            return json.loads(answers) or {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    if isinstance(answers, dict):
        return answers
    return {}


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, list):
        return ", ".join(str(v) for v in valor)
    return str(valor).strip()


def _parse_fecha(valor):
    texto = _texto(valor)
    if not texto:
        return None
    texto = texto[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            fecha = datetime.strptime(texto, fmt).date()
            if fecha.year < ANIO_MINIMO:
                return None
            return fecha
        except ValueError:
            continue
    return None


def _nombre_paciente(paciente):
    partes = [
        getattr(paciente, "primer_nombre", "") or "",
        getattr(paciente, "segundo_nombre", "") or "",
        getattr(paciente, "primer_apellido", "") or "",
        getattr(paciente, "segundo_apellido", "") or "",
    ]
    return " ".join(p.strip() for p in partes if p and str(p).strip())


def listar_sesiones_atenea():
    """Una fila por envío del examen 56 con campos de intervención normalizados."""
    qs = (
        ExamenSubmission.objects.filter(visita_examen__examen_id=EXAMEN_ANOSOGNOSIA_ID)
        .select_related("visita_examen__visita__paciente")
        .order_by("visita_examen__visita__paciente_id", "id")
    )
    sesiones = []
    for submission in qs:
        visita_examen = submission.visita_examen
        visita = visita_examen.visita if visita_examen else None
        paciente = visita.paciente if visita else None
        if paciente is None:
            continue
        answers = _como_dict(submission.answers)
        fecha = _parse_fecha(answers.get("Interv_fecha") or answers.get("interv_fecha"))
        sesiones.append(
            {
                "paciente_id": paciente.id,
                "documento": _texto(paciente.numero_documento),
                "nombre": _nombre_paciente(paciente),
                "correo": _texto(paciente.correo).lower(),
                "visita_examen_id": visita_examen.id,
                "sesion_no": _texto(answers.get("Interv_SesionNo")),
                "fecha": fecha.isoformat() if fecha else "",
                "fecha_obj": fecha,
                "hora_inicio": _texto(answers.get("Interv_horaInicio")),
                "hora_final": _texto(answers.get("Interv_horaFinal")),
                "asistencia": _texto(answers.get("Interv_Asistencia")),
                "asistio": _texto(answers.get("Interv_Asistio")),
                "nivel_participacion": _texto(answers.get("Interv_NivelParticipacion")),
                "destreza": _texto(answers.get("Interv_Destreza")),
                "estado_participante": _texto(answers.get("Interv_EstadoPArticipante")),
                "tematica": _texto(
                    answers.get("Interv_Temática") or answers.get("Interv_Tematica")
                ),
                "observaciones": _texto(answers.get("Interv_Observaciones")),
            }
        )
    return sesiones


def _indice_usuarios_por_email(usuarios):
    indice = {}
    for fila in usuarios:
        email = str(fila.get("email") or "").strip().lower()
        if email and "@" in email and email not in indice:
            indice[email] = fila
    return indice


def _dau_por_dia(date_from, date_to):
    """Mapa YYYY-MM-DD -> personas activas (serie DAU del endpoint de cohorte)."""
    series = recuerdame_analytics._por_serie(
        recuerdame_analytics._ejecutar_endpoint(
            recuerdame_analytics.ENDPOINT_COHORTE, date_from, date_to
        )
    )
    return {
        str(fila.get("clave"))[:10]: recuerdame_analytics._entero(fila.get("personas"))
        for fila in series.get("dau", [])
    }


def _ventana_fechas(sesiones):
    fechas = [s["fecha_obj"] for s in sesiones if s.get("fecha_obj")]
    if not fechas:
        hoy = datetime.now(ZONA).date()
        return hoy.isoformat(), hoy.isoformat()
    desde = min(fechas) - timedelta(days=1)
    hasta = max(fechas) + timedelta(days=1)
    return desde.isoformat(), hasta.isoformat()


def _dias_login(activity_user):
    dias = set()
    for login in (activity_user or {}).get("logins") or []:
        ts = str((login or {}).get("timestamp") or "")
        if ts:
            dias.add(ts[:10])
    return dias


def _campos_base(sesion):
    return {k: sesion[k] for k in (
        "paciente_id",
        "documento",
        "nombre",
        "correo",
        "visita_examen_id",
        "sesion_no",
        "fecha",
        "hora_inicio",
        "hora_final",
        "asistencia",
        "asistio",
        "nivel_participacion",
        "destreza",
        "estado_participante",
        "tematica",
        "observaciones",
    )}


def _campos_posthog(usuario):
    if usuario is None:
        return {
            "match_posthog": "no",
            "person_id": "",
            "adherencia_pct": "",
            "sesiones_posthog": "",
            "pageviews_posthog": "",
            "duracion_media_sesion_seg": "",
            "amplitud_secciones": "",
            "rol_aproximado": "",
            "dispositivo_principal": "",
            "primera_actividad": "",
            "ultima_actividad": "",
        }
    rol_clave = recuerdame_analytics._clave(usuario.get("rol_aproximado"))
    rol = recuerdame_analytics.ROLES.get(rol_clave, usuario.get("rol_aproximado") or "")
    disp = str(usuario.get("dispositivo_principal") or "")
    dispositivo = recuerdame_analytics.DISPOSITIVOS.get(disp.lower(), disp)
    return {
        "match_posthog": "sí",
        "person_id": usuario.get("person_id") or "",
        "adherencia_pct": recuerdame_analytics._adherencia_pct(usuario),
        "sesiones_posthog": recuerdame_analytics._entero(usuario.get("sesiones")),
        "pageviews_posthog": recuerdame_analytics._entero(usuario.get("pageviews")),
        "duracion_media_sesion_seg": usuario.get("duracion_media_sesion_seg") or "",
        "amplitud_secciones": recuerdame_analytics._entero(
            usuario.get("amplitud_secciones")
        ),
        "rol_aproximado": rol,
        "dispositivo_principal": dispositivo,
        "primera_actividad": usuario.get("primera_actividad") or "",
        "ultima_actividad": usuario.get("ultima_actividad") or "",
    }


def _campos_activity(activity_user, fecha_sesion):
    if not activity_user:
        return {
            "match_recuerdame": "no",
            "mongo_id": "",
            "logins_en_ventana": "",
            "dias_con_login": "",
            "sesiones_juego": "",
            "login_ese_dia": "no",
        }
    dias = _dias_login(activity_user)
    return {
        "match_recuerdame": "sí",
        "mongo_id": activity_user.get("mongo_id") or "",
        "logins_en_ventana": activity_user.get("logins_count", len(activity_user.get("logins") or [])),
        "dias_con_login": len(dias),
        "sesiones_juego": activity_user.get(
            "sessions_count", len(activity_user.get("sessions") or [])
        ),
        "login_ese_dia": "sí" if fecha_sesion and fecha_sesion in dias else "no",
    }


def _resolver_activity(sesion, por_email, por_documento):
    if sesion.get("correo") and sesion["correo"] in por_email:
        return por_email[sesion["correo"]]
    if sesion.get("documento") and sesion["documento"] in por_documento:
        return por_documento[sesion["documento"]]
    return None


def _enriquecer_fila(sesion, usuario_posthog, personas_dia, activity_user):
    fila = _campos_base(sesion)
    fila.update(_campos_posthog(usuario_posthog))
    fila["personas_activas_dia"] = personas_dia
    fila.update(_campos_activity(activity_user, sesion.get("fecha")))
    return fila


def _resumen_pacientes(filas):
    por_paciente = {}
    for fila in filas:
        clave = fila["paciente_id"]
        bucket = por_paciente.setdefault(
            clave,
            {
                "paciente_id": fila["paciente_id"],
                "documento": fila["documento"],
                "nombre": fila["nombre"],
                "correo": fila["correo"],
                "sesiones": 0,
                "fechas": [],
                "match_posthog": False,
                "match_recuerdame": False,
                "person_id": "",
                "mongo_id": "",
                "adherencia_pct": "",
                "sesiones_posthog": "",
                "logins_en_ventana": "",
                "dias_con_login": "",
                "sesiones_juego": "",
                "dias_con_actividad_recuerdame": 0,
                "dias_con_login_intervencion": 0,
            },
        )
        bucket["sesiones"] += 1
        if fila["fecha"]:
            bucket["fechas"].append(fila["fecha"])
        if fila["match_posthog"] == "sí":
            bucket["match_posthog"] = True
            bucket["person_id"] = fila["person_id"]
            bucket["adherencia_pct"] = fila["adherencia_pct"]
            bucket["sesiones_posthog"] = fila["sesiones_posthog"]
        if fila["match_recuerdame"] == "sí":
            bucket["match_recuerdame"] = True
            bucket["mongo_id"] = fila["mongo_id"]
            bucket["logins_en_ventana"] = fila["logins_en_ventana"]
            bucket["dias_con_login"] = fila["dias_con_login"]
            bucket["sesiones_juego"] = fila["sesiones_juego"]
        if recuerdame_analytics._entero(fila.get("personas_activas_dia")) > 0:
            bucket["dias_con_actividad_recuerdame"] += 1
        if fila.get("login_ese_dia") == "sí":
            bucket["dias_con_login_intervencion"] += 1

    pacientes = []
    for bucket in por_paciente.values():
        fechas = sorted(bucket["fechas"])
        pacientes.append(
            {
                "paciente_id": bucket["paciente_id"],
                "documento": bucket["documento"],
                "nombre": bucket["nombre"],
                "correo": bucket["correo"],
                "sesiones": bucket["sesiones"],
                "primera_sesion": fechas[0] if fechas else "",
                "ultima_sesion": fechas[-1] if fechas else "",
                "match_posthog": "sí" if bucket["match_posthog"] else "no",
                "match_recuerdame": "sí" if bucket["match_recuerdame"] else "no",
                "person_id": bucket["person_id"],
                "mongo_id": bucket["mongo_id"],
                "adherencia_pct": bucket["adherencia_pct"],
                "sesiones_posthog": bucket["sesiones_posthog"],
                "logins_en_ventana": bucket["logins_en_ventana"],
                "dias_con_login": bucket["dias_con_login"],
                "sesiones_juego": bucket["sesiones_juego"],
                "dias_con_actividad_recuerdame": bucket["dias_con_actividad_recuerdame"],
                "dias_con_login_intervencion": bucket["dias_con_login_intervencion"],
            }
        )
    pacientes.sort(
        key=lambda p: (
            -int(p["match_recuerdame"] == "sí"),
            -int(p["match_posthog"] == "sí"),
            p["nombre"].lower(),
        )
    )
    return pacientes


def construir_cruce():
    """Arma el cruce completo: sesiones enriquecidas, pacientes y KPIs."""
    sesiones = listar_sesiones_atenea()
    date_from, date_to = _ventana_fechas(sesiones)

    usuarios = []
    dau = {}
    error_posthog = None
    try:
        usuarios = recuerdame_analytics.obtener_usuarios(date_from, date_to)
        dau = _dau_por_dia(date_from, date_to)
    except recuerdame_analytics.RecuerdameAnalyticsError as exc:
        error_posthog = str(exc)
        logger.warning("Cruce Anosognosia sin PostHog: %s", exc)

    error_activity = None
    por_email_act = {}
    por_doc_act = {}
    if recuerdame_activity_api.configurado():
        emails = sorted({s["correo"] for s in sesiones if s.get("correo")})
        docs = sorted({s["documento"] for s in sesiones if s.get("documento")})
        try:
            datos = recuerdame_activity_api.consultar_actividad(
                emails, docs, date_from, date_to
            )
            por_email_act, por_doc_act = (
                recuerdame_activity_api.indice_por_email_y_documento(datos)
            )
        except recuerdame_activity_api.RecuerdameActivityError as exc:
            error_activity = str(exc)
            logger.warning("Cruce Anosognosia sin API actividad: %s", exc)
    else:
        error_activity = (
            "API de actividad RecuérdaMe no configurada "
            "(RECUERDAME_API_URL / RECUERDAME_ATENEA_API_KEY)."
        )

    por_email = _indice_usuarios_por_email(usuarios)
    filas = []
    for sesion in sesiones:
        usuario = por_email.get(sesion["correo"]) if sesion["correo"] else None
        personas_dia = dau.get(sesion["fecha"], 0) if sesion["fecha"] else 0
        activity_user = _resolver_activity(sesion, por_email_act, por_doc_act)
        filas.append(_enriquecer_fila(sesion, usuario, personas_dia, activity_user))

    pacientes = _resumen_pacientes(filas)
    con_match_ph = sum(1 for p in pacientes if p["match_posthog"] == "sí")
    con_match_rm = sum(1 for p in pacientes if p["match_recuerdame"] == "sí")
    fechas_unicas = {f["fecha"] for f in filas if f["fecha"]}
    dias_con_actividad = sum(1 for f in fechas_unicas if dau.get(f, 0) > 0)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "filas": filas,
        "pacientes": pacientes,
        "error_posthog": error_posthog,
        "error_activity": error_activity,
        "kpis": {
            "pacientes": len(pacientes),
            "sesiones": len(filas),
            "con_match_email": con_match_ph,
            "con_match_recuerdame": con_match_rm,
            "fechas_intervencion": len(fechas_unicas),
            "fechas_con_actividad_recuerdame": dias_con_actividad,
        },
        "actividad_dias": {
            "labels": sorted(fechas_unicas),
            "values": [dau.get(d, 0) for d in sorted(fechas_unicas)],
        },
    }


def construir_tabla_csv(cruce=None):
    """(encabezados, filas) — un único CSV con todas las sesiones enriquecidas."""
    if cruce is None:
        cruce = construir_cruce()
    encabezados = [etiqueta for _, etiqueta in COLUMNAS_CSV]
    filas = []
    for fila in cruce["filas"]:
        filas.append(
            [
                recuerdame_analytics._celda_segura(fila.get(clave))
                for clave, _ in COLUMNAS_CSV
            ]
        )
    return encabezados, filas
