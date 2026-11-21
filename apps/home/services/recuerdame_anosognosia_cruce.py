# -*- encoding: utf-8 -*-
"""
Cruce Atenea × PostHog × RecuérdaMe (actividad autenticada) para Anosognosia
(examen form builder 56).

Une las sesiones clínicas (``Interv_fecha`` + horas + correo/documento) con:

- Biomarcadores PostHog (match por correo o ``horario_unico``).
- Candidatos PostHog a nivel franja (``horario_grupo``, sin 1:1).
- Personas activas ese día (serie DAU PostHog).
- Cuenta RecuérdaMe + login_logs + sessionGame vía
  ``POST /v1/integrations/atenea/activity``.

Ámbito (``match_scope``): ``paciente`` | ``franja`` | ``ninguno``.
Confianza: ``alta`` (email / horario_unico) | ``media`` (grupo) | ``baja``.
"""
from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apps.home.models.exam_builder import ExamenSubmission

from . import recuerdame_activity_api, recuerdame_analytics

logger = logging.getLogger(__name__)

EXAMEN_ANOSOGNOSIA_ID = 56
ZONA = ZoneInfo("America/Bogota")
ANIO_MINIMO = 2025
TOLERANCIA_MINUTOS = 15
MAX_VENTANA_EFECTIVA_HORAS = 2

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
    ("match_scope", "Ámbito match"),
    ("match_origen", "Origen match"),
    ("match_confianza", "Confianza match"),
    ("atribuible", "Atribuible"),
    ("person_id", "ID persona PostHog"),
    ("person_ids_candidatos", "Person IDs candidatos franja"),
    ("n_pacientes", "Pacientes en franja"),
    ("n_personas", "Personas PostHog en franja"),
    ("adherencia_pct", "Adherencia PostHog (%)"),
    ("sesiones_posthog", "Sesiones PostHog"),
    ("pageviews_posthog", "Vistas PostHog"),
    ("duracion_media_sesion_seg", "Duración media sesión PostHog (s)"),
    ("amplitud_secciones", "Amplitud secciones"),
    ("rol_aproximado", "Rol aproximado"),
    ("dispositivo_principal", "Dispositivo principal"),
    ("primera_actividad", "Primera actividad PostHog"),
    ("ultima_actividad", "Última actividad PostHog"),
    ("franja_adherencia_mediana", "Franja adherencia mediana (%)"),
    ("franja_sesiones_suma", "Franja sesiones suma"),
    ("franja_pageviews_suma", "Franja vistas suma"),
    ("personas_activas_dia", "Personas activas RecuérdaMe ese día"),
    ("match_recuerdame", "Match cuenta RecuérdaMe"),
    ("mongo_id", "ID Mongo RecuérdaMe"),
    ("logins_en_ventana", "Logins en ventana"),
    ("dias_con_login", "Días con login"),
    ("sesiones_juego", "Sesiones de juego"),
    ("login_ese_dia", "Login ese día"),
    ("login_en_horario", "Login en horario clínico"),
    ("logins_en_horario", "Logins en horario clínico"),
    ("juego_en_horario", "Juego en horario clínico"),
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


def _parse_hora(valor):
    """Devuelve (hour, minute, second) o None."""
    texto = _texto(valor)
    if not texto:
        return None
    texto = texto.replace(".", ":").strip()
    for fmt in ("%H:%M:%S", "%H:%M", "%H"):
        try:
            t = datetime.strptime(texto[:8] if fmt != "%H" else texto[:2], fmt).time()
            return t.hour, t.minute, t.second
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
            if recuerdame_analytics.es_email_staff(email):
                continue
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


def construir_ventana_clinica(fecha, hora_inicio, hora_final, tolerancia_min=TOLERANCIA_MINUTOS):
    """(inicio, fin, meta) en America/Bogota o (None, None, meta) si no hay horas.

    ``meta`` incluye ``solapamiento_amplio`` y duración efectiva.
    """
    meta = {
        "tiene_horas": False,
        "solapamiento_amplio": False,
        "duracion_efectiva_horas": None,
        "tolerancia_min": tolerancia_min,
    }
    if not fecha:
        return None, None, meta
    hi = _parse_hora(hora_inicio)
    hf = _parse_hora(hora_final)
    if hi is None:
        return None, None, meta
    meta["tiene_horas"] = True
    inicio = datetime(
        fecha.year, fecha.month, fecha.day, hi[0], hi[1], hi[2], tzinfo=ZONA
    )
    if hf is None:
        fin = inicio + timedelta(hours=1)
    else:
        fin = datetime(
            fecha.year, fecha.month, fecha.day, hf[0], hf[1], hf[2], tzinfo=ZONA
        )
        if fin <= inicio:
            fin = fin + timedelta(days=1)
    tolerancia = timedelta(minutes=tolerancia_min)
    inicio_t = inicio - tolerancia
    fin_t = fin + tolerancia
    duracion_h = (fin_t - inicio_t).total_seconds() / 3600.0
    meta["duracion_efectiva_horas"] = round(duracion_h, 2)
    if tolerancia_min != TOLERANCIA_MINUTOS or duracion_h > MAX_VENTANA_EFECTIVA_HORAS:
        meta["solapamiento_amplio"] = True
    return inicio_t, fin_t, meta


def _clave_franja(sesion):
    return (
        sesion.get("fecha") or "",
        sesion.get("hora_inicio") or "",
        sesion.get("hora_final") or "",
    )


def personas_en_ventana(actividad, inicio, fin):
    """Set de person_id con al menos un timestamp en [inicio, fin]."""
    if inicio is None or fin is None:
        return set()
    ids = set()
    for item in actividad or []:
        ts = item.get("timestamp")
        pid = item.get("person_id")
        if not pid or ts is None:
            continue
        if inicio <= ts <= fin:
            ids.add(pid)
    return ids


def clasificar_match_horario(n_pacientes, n_personas, solapamiento_amplio=False):
    """Devuelve dict con scope/origen/confianza/atribuible (sin email)."""
    if n_personas <= 0:
        return {
            "match_scope": "ninguno",
            "match_origen": "ninguno",
            "match_confianza": "",
            "atribuible": "no",
        }
    if n_pacientes == 1 and n_personas == 1 and not solapamiento_amplio:
        return {
            "match_scope": "paciente",
            "match_origen": "horario_unico",
            "match_confianza": "alta",
            "atribuible": "sí",
        }
    if n_personas == 1 and n_pacientes > 1:
        return {
            "match_scope": "franja",
            "match_origen": "horario_grupo",
            "match_confianza": "baja",
            "atribuible": "no",
        }
    confianza = "baja" if solapamiento_amplio or n_personas > 2 * max(n_pacientes, 1) else "media"
    if solapamiento_amplio and n_personas > 2 * max(n_pacientes, 1):
        scope = "franja"
    else:
        scope = "franja"
    return {
        "match_scope": scope,
        "match_origen": "horario_grupo",
        "match_confianza": confianza,
        "atribuible": "no",
    }


def _agregados_franja(person_ids, por_person_id):
    adherencias = []
    sesiones = 0
    pageviews = 0
    for pid in person_ids:
        u = por_person_id.get(pid)
        if not u:
            continue
        adherencias.append(recuerdame_analytics._adherencia_pct(u))
        sesiones += recuerdame_analytics._entero(u.get("sesiones"))
        pageviews += recuerdame_analytics._entero(u.get("pageviews"))
    return {
        "franja_adherencia_mediana": (
            round(recuerdame_analytics._mediana(adherencias), 1) if adherencias else ""
        ),
        "franja_sesiones_suma": sesiones if person_ids else "",
        "franja_pageviews_suma": pageviews if person_ids else "",
    }


def _campos_posthog_vacios():
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


def _campos_posthog_paciente(usuario):
    if usuario is None:
        return _campos_posthog_vacios()
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


def _parse_ts_activity(valor):
    return recuerdame_analytics._parse_ts_bogota(valor)


def _dias_login(activity_user):
    dias = set()
    for login in (activity_user or {}).get("logins") or []:
        ts = str((login or {}).get("timestamp") or "")
        if ts:
            dias.add(ts[:10])
    return dias


def _flags_horario_activity(activity_user, inicio, fin):
    if not activity_user or inicio is None or fin is None:
        return {
            "login_en_horario": "no" if activity_user else "",
            "logins_en_horario": 0 if activity_user else "",
            "juego_en_horario": "no" if activity_user else "",
        }
    logins_n = 0
    for login in activity_user.get("logins") or []:
        ts = _parse_ts_activity((login or {}).get("timestamp"))
        if ts is not None and inicio <= ts <= fin:
            logins_n += 1
    juego = False
    for sess in activity_user.get("sessions") or []:
        start = _parse_ts_activity((sess or {}).get("startDate") or (sess or {}).get("start_date"))
        end = _parse_ts_activity((sess or {}).get("finalDate") or (sess or {}).get("final_date"))
        if start is None and end is None:
            continue
        s = start or end
        e = end or start
        if s <= fin and e >= inicio:
            juego = True
            break
    return {
        "login_en_horario": "sí" if logins_n else "no",
        "logins_en_horario": logins_n,
        "juego_en_horario": "sí" if juego else "no",
    }


def _campos_activity(activity_user, fecha_sesion, inicio, fin):
    if not activity_user:
        return {
            "match_recuerdame": "no",
            "mongo_id": "",
            "logins_en_ventana": "",
            "dias_con_login": "",
            "sesiones_juego": "",
            "login_ese_dia": "no",
            "login_en_horario": "",
            "logins_en_horario": "",
            "juego_en_horario": "",
        }
    dias = _dias_login(activity_user)
    base = {
        "match_recuerdame": "sí",
        "mongo_id": activity_user.get("mongo_id") or "",
        "logins_en_ventana": activity_user.get(
            "logins_count", len(activity_user.get("logins") or [])
        ),
        "dias_con_login": len(dias),
        "sesiones_juego": activity_user.get(
            "sessions_count", len(activity_user.get("sessions") or [])
        ),
        "login_ese_dia": "sí" if fecha_sesion and fecha_sesion in dias else "no",
    }
    base.update(_flags_horario_activity(activity_user, inicio, fin))
    return base


def _resolver_activity(sesion, por_email, por_documento):
    if sesion.get("correo") and sesion["correo"] in por_email:
        return por_email[sesion["correo"]]
    if sesion.get("documento") and sesion["documento"] in por_documento:
        return por_documento[sesion["documento"]]
    return None


def _campos_base(sesion):
    return {
        k: sesion[k]
        for k in (
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
        )
    }


def _construir_info_franjas(sesiones, actividad):
    """Por clave de franja: n_pacientes, person_ids, meta de ventana, clasificación."""
    por_clave = defaultdict(list)
    for sesion in sesiones:
        por_clave[_clave_franja(sesion)].append(sesion)

    info = {}
    for clave, grupo in por_clave.items():
        pacientes = {s["paciente_id"] for s in grupo}
        n_pacientes = len(pacientes)
        muestra = grupo[0]
        inicio, fin, meta = construir_ventana_clinica(
            muestra.get("fecha_obj"),
            muestra.get("hora_inicio"),
            muestra.get("hora_final"),
        )
        person_ids = sorted(personas_en_ventana(actividad, inicio, fin))
        n_personas = len(person_ids)
        amplio = bool(meta.get("solapamiento_amplio"))
        if n_personas > 2 * max(n_pacientes, 1):
            amplio = True
        clasif = clasificar_match_horario(n_pacientes, n_personas, amplio)
        info[clave] = {
            "n_pacientes": n_pacientes,
            "n_personas": n_personas,
            "person_ids": person_ids,
            "inicio": inicio,
            "fin": fin,
            "meta": meta,
            "clasificacion": clasif,
        }
    return info


def _resolver_person_id_horario_unico(paciente_id, filas_unicas_candidatos):
    """Entre varias franjas unicas del paciente, el person_id más frecuente.

    Si hay empate conflictivo (varios ids con misma frecuencia máxima >0 y
    más de un id distinto), retorna None (conflicto).
    """
    contador = Counter(filas_unicas_candidatos.get(paciente_id) or [])
    if not contador:
        return None
    max_n = max(contador.values())
    top = [pid for pid, n in contador.items() if n == max_n]
    if len(top) == 1:
        return top[0]
    return None


def _enriquecer_filas(sesiones, usuarios, dau, actividad, por_email_act, por_doc_act):
    por_email = _indice_usuarios_por_email(usuarios)
    por_person_id = recuerdame_analytics.indice_usuarios_por_person_id(usuarios)
    franjas = _construir_info_franjas(sesiones, actividad)

    # Primera pasada: candidatos horario_unico por paciente (sin email)
    unicos_por_paciente = defaultdict(list)
    for sesion in sesiones:
        if sesion.get("correo") and sesion["correo"] in por_email:
            continue
        info = franjas.get(_clave_franja(sesion)) or {}
        clasif = info.get("clasificacion") or {}
        if (
            clasif.get("match_origen") == "horario_unico"
            and clasif.get("atribuible") == "sí"
            and info.get("person_ids")
        ):
            unicos_por_paciente[sesion["paciente_id"]].append(info["person_ids"][0])

    person_unico_estable = {
        pid: _resolver_person_id_horario_unico(pid, unicos_por_paciente)
        for pid in unicos_por_paciente
    }

    filas = []
    for sesion in sesiones:
        clave = _clave_franja(sesion)
        info = franjas.get(clave) or {
            "n_pacientes": 1,
            "n_personas": 0,
            "person_ids": [],
            "inicio": None,
            "fin": None,
            "meta": {},
            "clasificacion": clasificar_match_horario(1, 0),
        }
        inicio, fin = info.get("inicio"), info.get("fin")
        activity_user = _resolver_activity(sesion, por_email_act, por_doc_act)
        personas_dia = dau.get(sesion["fecha"], 0) if sesion["fecha"] else 0

        fila = _campos_base(sesion)
        fila["personas_activas_dia"] = personas_dia
        fila.update(_campos_activity(activity_user, sesion.get("fecha"), inicio, fin))
        fila["n_pacientes"] = info["n_pacientes"]
        fila["n_personas"] = info["n_personas"]
        fila["person_ids_candidatos"] = ",".join(info["person_ids"])
        fila.update(
            {
                "franja_adherencia_mediana": "",
                "franja_sesiones_suma": "",
                "franja_pageviews_suma": "",
            }
        )

        usuario_email = (
            por_email.get(sesion["correo"]) if sesion.get("correo") else None
        )
        if usuario_email is not None:
            fila.update(_campos_posthog_paciente(usuario_email))
            fila["match_scope"] = "paciente"
            fila["match_origen"] = "email"
            fila["match_confianza"] = "alta"
            fila["atribuible"] = "sí"
            filas.append(fila)
            continue

        clasif = dict(info["clasificacion"])
        person_ids = info["person_ids"]

        if clasif["match_origen"] == "horario_unico" and person_ids:
            pid = person_unico_estable.get(sesion["paciente_id"])
            if pid is None and len(person_ids) == 1:
                # Conflicto entre sesiones: no atribuir biomarcadores
                clasif = {
                    "match_scope": "paciente",
                    "match_origen": "horario_unico",
                    "match_confianza": "baja",
                    "atribuible": "no",
                }
                fila.update(_campos_posthog_vacios())
                fila["match_posthog"] = "candidato"
                fila["person_ids_candidatos"] = ",".join(
                    sorted(set(unicos_por_paciente.get(sesion["paciente_id"]) or person_ids))
                )
            elif pid is None:
                fila.update(_campos_posthog_vacios())
                fila["match_posthog"] = "no"
            else:
                usuario = por_person_id.get(pid)
                fila.update(_campos_posthog_paciente(usuario or {"person_id": pid}))
                if usuario is None:
                    fila["match_posthog"] = "sí"
                    fila["person_id"] = pid
            fila.update(clasif)
            filas.append(fila)
            continue

        if clasif["match_origen"] == "horario_grupo" and person_ids:
            # Sin biomarcadores individuales; agregados de franja; no copiar person_id
            fila.update(_campos_posthog_vacios())
            fila["match_posthog"] = "candidato"
            fila.update(_agregados_franja(person_ids, por_person_id))
            fila.update(clasif)
            # M=1 N>1: candidato solo a nivel slot (ya en person_ids_candidatos), no en person_id
            filas.append(fila)
            continue

        fila.update(_campos_posthog_vacios())
        fila.update(clasif)
        filas.append(fila)

    return filas, franjas


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
                "pageviews_posthog": "",
                "dispositivo_principal": "",
                "rol_aproximado": "",
                "logins_en_ventana": "",
                "dias_con_login": "",
                "sesiones_juego": "",
                "dias_con_actividad_recuerdame": 0,
                "dias_con_login_intervencion": 0,
                "sesiones_login_horario": 0,
                "sesiones_juego_horario": 0,
                "franjas_grupo": 0,
                "person_ids_franja": set(),
                "match_scope": "ninguno",
                "match_origen": "ninguno",
                "match_confianza": "",
                "atribuible": "no",
            },
        )
        bucket["sesiones"] += 1
        if fila["fecha"]:
            bucket["fechas"].append(fila["fecha"])
        if fila.get("match_posthog") == "sí" and fila.get("atribuible") == "sí":
            bucket["match_posthog"] = True
            bucket["person_id"] = fila.get("person_id") or bucket["person_id"]
            bucket["adherencia_pct"] = fila.get("adherencia_pct") or bucket["adherencia_pct"]
            bucket["sesiones_posthog"] = (
                fila.get("sesiones_posthog") or bucket["sesiones_posthog"]
            )
            bucket["pageviews_posthog"] = (
                fila.get("pageviews_posthog") or bucket["pageviews_posthog"]
            )
            bucket["dispositivo_principal"] = (
                fila.get("dispositivo_principal") or bucket["dispositivo_principal"]
            )
            bucket["rol_aproximado"] = (
                fila.get("rol_aproximado") or bucket["rol_aproximado"]
            )
            bucket["match_scope"] = fila.get("match_scope") or bucket["match_scope"]
            bucket["match_origen"] = fila.get("match_origen") or bucket["match_origen"]
            bucket["match_confianza"] = (
                fila.get("match_confianza") or bucket["match_confianza"]
            )
            bucket["atribuible"] = "sí"
        elif (
            not bucket["match_posthog"]
            and fila.get("match_scope") == "franja"
            and bucket["match_scope"] == "ninguno"
        ):
            bucket["match_scope"] = "franja"
            bucket["match_origen"] = fila.get("match_origen") or "horario_grupo"
            bucket["match_confianza"] = fila.get("match_confianza") or ""
            bucket["atribuible"] = "no"
        if fila.get("match_scope") == "franja":
            bucket["franjas_grupo"] += 1
            for pid in str(fila.get("person_ids_candidatos") or "").split(","):
                pid = pid.strip()
                if pid:
                    bucket["person_ids_franja"].add(pid)
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
        if fila.get("login_en_horario") == "sí":
            bucket["sesiones_login_horario"] += 1
        if fila.get("juego_en_horario") == "sí":
            bucket["sesiones_juego_horario"] += 1

    pacientes = []
    for bucket in por_paciente.values():
        fechas = sorted(bucket["fechas"])
        sesiones = bucket["sesiones"] or 1
        ratio = round(100.0 * bucket["sesiones_login_horario"] / sesiones, 1)
        ids_franja = sorted(bucket["person_ids_franja"])
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
                "person_id_corto": recuerdame_analytics.person_id_corto(
                    bucket["person_id"]
                ),
                "mongo_id": bucket["mongo_id"],
                "adherencia_pct": bucket["adherencia_pct"],
                "sesiones_posthog": bucket["sesiones_posthog"],
                "pageviews_posthog": bucket["pageviews_posthog"],
                "dispositivo_principal": bucket["dispositivo_principal"],
                "rol_aproximado": bucket["rol_aproximado"],
                "logins_en_ventana": bucket["logins_en_ventana"],
                "dias_con_login": bucket["dias_con_login"],
                "sesiones_juego": bucket["sesiones_juego"],
                "dias_con_actividad_recuerdame": bucket["dias_con_actividad_recuerdame"],
                "dias_con_login_intervencion": bucket["dias_con_login_intervencion"],
                "sesiones_login_horario": bucket["sesiones_login_horario"],
                "sesiones_juego_horario": bucket["sesiones_juego_horario"],
                "pct_login_horario": ratio,
                "franjas_grupo": bucket["franjas_grupo"],
                "person_ids_franja": ids_franja,
                "person_ids_franja_txt": ",".join(ids_franja),
                "n_candidatos_franja": len(ids_franja),
                "match_scope": bucket["match_scope"],
                "match_origen": bucket["match_origen"],
                "match_confianza": bucket["match_confianza"],
                "atribuible": bucket["atribuible"],
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


def resumen_franjas(franjas, usuarios=None):
    """Lista de franjas para auditoría/UI (IDs + etiquetas cuando existan)."""
    por_person_id = recuerdame_analytics.indice_usuarios_por_person_id(usuarios)
    salida = []
    for clave, info in sorted(franjas.items(), key=lambda x: x[0]):
        fecha, hi, hf = clave
        clasif = info.get("clasificacion") or {}
        pids = list(info.get("person_ids") or [])
        personas = [
            recuerdame_analytics.etiqueta_persona(por_person_id.get(pid), pid)
            for pid in pids
        ]
        personas.sort(key=lambda p: (not p["identificado"], p["etiqueta"].lower()))
        salida.append(
            {
                "fecha": fecha,
                "hora_inicio": hi,
                "hora_final": hf,
                "n_pacientes": info.get("n_pacientes", 0),
                "n_personas": info.get("n_personas", 0),
                "person_ids": pids,
                "personas": personas,
                "person_ids_txt": ",".join(pids),
                "match_scope": clasif.get("match_scope", ""),
                "match_origen": clasif.get("match_origen", ""),
                "match_confianza": clasif.get("match_confianza", ""),
                "atribuible": clasif.get("atribuible", "no"),
                "solapamiento_amplio": bool(
                    (info.get("meta") or {}).get("solapamiento_amplio")
                ),
            }
        )
    return salida


def construir_cruce():
    """Arma el cruce completo: sesiones enriquecidas, pacientes, franjas y KPIs."""
    sesiones = listar_sesiones_atenea()
    date_from, date_to = _ventana_fechas(sesiones)

    usuarios = []
    dau = {}
    actividad = []
    error_posthog = None
    try:
        usuarios = recuerdame_analytics.obtener_usuarios(date_from, date_to)
        dau = _dau_por_dia(date_from, date_to)
    except recuerdame_analytics.RecuerdameAnalyticsError as exc:
        error_posthog = str(exc)
        logger.warning("Cruce Anosognosia sin PostHog biomarcadores: %s", exc)

    try:
        actividad = recuerdame_analytics.obtener_actividad_personas(date_from, date_to)
    except recuerdame_analytics.RecuerdameAnalyticsError as exc:
        if error_posthog is None:
            error_posthog = str(exc)
        else:
            error_posthog = f"{error_posthog} | Actividad horario: {exc}"
        logger.warning("Cruce Anosognosia sin actividad PostHog por hora: %s", exc)

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

    filas, franjas = _enriquecer_filas(
        sesiones, usuarios, dau, actividad, por_email_act, por_doc_act
    )
    pacientes = _resumen_pacientes(filas)
    franjas_lista = resumen_franjas(franjas, usuarios)

    con_match_paciente = sum(
        1
        for p in pacientes
        if p["match_posthog"] == "sí" and p.get("atribuible") == "sí"
    )
    con_match_email = sum(
        1 for f in filas if f.get("match_origen") == "email"
    )
    # pacientes únicos con al menos una sesión email
    pacientes_email = {
        f["paciente_id"] for f in filas if f.get("match_origen") == "email"
    }
    pacientes_horario_unico = {
        f["paciente_id"]
        for f in filas
        if f.get("match_origen") == "horario_unico" and f.get("atribuible") == "sí"
    }
    sesiones_horario_unico = sum(
        1
        for f in filas
        if f.get("match_origen") == "horario_unico" and f.get("atribuible") == "sí"
    )
    sesiones_grupo = sum(
        1 for f in filas if f.get("match_origen") == "horario_grupo"
    )
    sesiones_no_atribuible = sum(
        1
        for f in filas
        if f.get("match_scope") == "franja" and f.get("atribuible") == "no"
    )
    con_match_rm = sum(1 for p in pacientes if p["match_recuerdame"] == "sí")
    sesiones_login_horario = sum(
        1 for f in filas if f.get("login_en_horario") == "sí"
    )
    fechas_unicas = {f["fecha"] for f in filas if f["fecha"]}
    dias_con_actividad = sum(1 for f in fechas_unicas if dau.get(f, 0) > 0)

    # Preferir conteo HogQL por día de intervención; fallback DAU agregado
    personas_por_dia = recuerdame_analytics.construir_personas_por_dia(
        actividad, usuarios, fechas_filtro=fechas_unicas
    )
    # Si hay atribución 1:1 Atenea→person_id, preferir nombre clínico como etiqueta
    pid_a_paciente = {
        p["person_id"]: p for p in pacientes if p.get("person_id") and p.get("atribuible") == "sí"
    }
    for lista in personas_por_dia.values():
        for item in lista:
            pac = pid_a_paciente.get(item.get("person_id"))
            if not pac:
                continue
            etiqueta = pac.get("nombre") or pac.get("correo") or item.get("etiqueta")
            item["etiqueta"] = etiqueta
            item["identificado"] = True
    labels_dias = sorted(fechas_unicas)
    values_dias = [
        len(personas_por_dia.get(d, [])) or dau.get(d, 0) for d in labels_dias
    ]

    return {
        "date_from": date_from,
        "date_to": date_to,
        "filas": filas,
        "pacientes": pacientes,
        "franjas": franjas_lista,
        "error_posthog": error_posthog,
        "error_activity": error_activity,
        "kpis": {
            "pacientes": len(pacientes),
            "sesiones": len(filas),
            "con_match_email": len(pacientes_email),
            "con_match_paciente": con_match_paciente,
            "con_match_horario_unico": len(pacientes_horario_unico),
            "sesiones_horario_unico": sesiones_horario_unico,
            "sesiones_horario_grupo": sesiones_grupo,
            "sesiones_no_atribuible": sesiones_no_atribuible,
            "con_match_recuerdame": con_match_rm,
            "sesiones_con_login_horario": sesiones_login_horario,
            "fechas_intervencion": len(fechas_unicas),
            "fechas_con_actividad_recuerdame": dias_con_actividad,
            "filas_match_email": con_match_email,
        },
        "actividad_dias": {
            "labels": labels_dias,
            "values": values_dias,
        },
        "personas_por_dia": personas_por_dia,
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
