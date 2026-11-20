# -*- encoding: utf-8 -*-
"""
Biomarcadores digitales de RecuérdaMe.

Consulta dos endpoints guardados en PostHog (Endpoints API) y entrega los datos
ya normalizados a las vistas del dashboard y a la descarga CSV:

- ``recuerdame-biomarcadores-usuarios``: una fila por persona (``person_id``).
- ``recuerdame-biomarcadores-cohorte``: series agregadas del periodo en formato
  largo con columnas ``serie, clave, personas, sesiones, vistas, eventos``.
  Series: ``total`` (una fila, clave=total), ``dau`` (clave=YYYY-MM-DD),
  ``seccion`` (las 12 secciones), ``dispositivo`` (Desktop/Mobile/Tablet/
  Desconocido) y ``hora`` ("00".."23", America/Bogota).

Llamada: ``POST /api/projects/{id}/endpoints/<nombre>/run`` con Bearer de API key
personal y cuerpo ``{"variables": {"date_from", "date_to"}, "limit": 10000}``.
La respuesta trae ``columns`` + ``results`` (filas posicionales) y se convierte
con ``dict(zip(columns, fila))``.

Los errores de PostHog se registran en el log y se elevan como
``RecuerdameAnalyticsError`` con un mensaje seguro para mostrar en el navegador.
"""
import logging
import statistics
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

ENDPOINT_USUARIOS = "recuerdame-biomarcadores-usuarios"
ENDPOINT_COHORTE = "recuerdame-biomarcadores-cohorte"

ZONA_HORARIA = ZoneInfo("America/Bogota")
RANGOS_DIAS = (7, 30, 90, 180)
RANGO_DIAS_DEFECTO = 30

# (conexión, lectura) en segundos. HogQL sobre 180 días puede tardar.
TIMEOUT = (5, 45)
# Sin ``limit`` PostHog pagina con un tamaño pequeño y cortaría la lista de usuarios.
LIMITE_FILAS = 10000
CACHE_SEGUNDOS = 15 * 60

MENSAJE_ERROR = (
    "No fue posible obtener los datos de RecuérdaMe en este momento. "
    "Intente de nuevo en unos minutos."
)

# Único lugar donde se definen las secciones de contenido (clave -> etiqueta).
# El endpoint de usuarios entrega una columna ``vistas_<clave>`` por sección y el
# de cohorte usa la misma clave en la serie ``seccion``.
SECCIONES = {
    "poli_juego": "Poli-juego",
    "fortalece_tu_mente": "Fortalece tu mente",
    "hazlo_consciente": "Hazlo consciente",
    "pasatiempos": "Pasatiempos",
    "encuentros": "Encuentros",
    "informacion_salud": "Información en salud",
    "nutricion": "Nutrición",
    "sintomas": "Síntomas",
    "cambios_cognitivos": "Cambios cognitivos",
    "cuidados": "Cuidados",
    "comunicacion": "Comunicación",
    "companion": "Compañero",
}

DISPOSITIVOS = {
    "desktop": "Computador",
    "mobile": "Celular",
    "tablet": "Tablet",
    "desconocido": "Desconocido",
}

ROLES = {
    "participante": "Participante",
    "acompanante": "Acompañante",
    "cuidador": "Acompañante",
    "ambos": "Ambos",
}

# Columnas del endpoint de usuarios -> encabezado en español (orden del CSV).
COLUMNAS_USUARIOS = {
    "person_id": "ID de persona",
    "email": "Correo",
    "nombre": "Nombre",
    "dias_activos": "Días activos",
    "dias_ventana": "Días de la ventana",
    "adherencia": "Adherencia (%)",
    "sesiones": "Sesiones",
    "pageviews": "Vistas de página",
    "duracion_media_sesion_seg": "Duración media de sesión (s)",
    "autocapture_por_sesion": "Interacciones (autocapture) por sesión",
    "amplitud_secciones": "Amplitud de secciones",
    "recencia_dias": "Días desde la última actividad",
    "rol_aproximado": "Rol aproximado",
}
COLUMNAS_USUARIOS.update(
    {f"vistas_{k}": f"Vistas: {etiqueta}" for k, etiqueta in SECCIONES.items()}
)
COLUMNAS_USUARIOS.update(
    {
        "rageclicks": "Rageclicks",
        "primera_actividad": "Primera actividad",
        "ultima_actividad": "Última actividad",
        "dispositivo_principal": "Dispositivo principal",
    }
)


class RecuerdameAnalyticsError(Exception):
    """Fallo al consultar PostHog; ``str(error)`` es seguro para el usuario."""


# ---------------------------------------------------------------------------
# Rango de fechas
# ---------------------------------------------------------------------------


def normalizar_dias(valor):
    """Devuelve un rango válido (7/30/90/180); cualquier otro valor usa el defecto."""
    try:
        dias = int(valor)
    except (TypeError, ValueError):
        return RANGO_DIAS_DEFECTO
    return dias if dias in RANGOS_DIAS else RANGO_DIAS_DEFECTO


def rango_fechas(dias):
    """(date_from, date_to) en YYYY-MM-DD, hora de Bogotá, con ``date_to`` = hoy."""
    hoy = datetime.now(ZONA_HORARIA).date()
    desde = hoy - timedelta(days=dias - 1)
    return desde.isoformat(), hoy.isoformat()


# ---------------------------------------------------------------------------
# Llamada a PostHog
# ---------------------------------------------------------------------------


def _ejecutar_endpoint(nombre, date_from, date_to):
    """Ejecuta un endpoint de PostHog y devuelve una lista de dicts por fila."""
    clave_cache = f"recuerdame_bio:{nombre}:{date_from}:{date_to}"
    en_cache = cache.get(clave_cache)
    if en_cache is not None:
        return en_cache

    if not (
        settings.POSTHOG_API_URL
        and settings.POSTHOG_PROJECT_ID
        and settings.POSTHOG_PERSONAL_API_KEY
    ):
        logger.error("Faltan variables de configuración de PostHog.")
        raise RecuerdameAnalyticsError(MENSAJE_ERROR)

    url = (
        f"{settings.POSTHOG_API_URL.rstrip('/')}/api/projects/"
        f"{settings.POSTHOG_PROJECT_ID}/endpoints/{nombre}/run"
    )
    headers = {
        "Authorization": f"Bearer {settings.POSTHOG_PERSONAL_API_KEY}",
        "Content-Type": "application/json",
    }
    cuerpo = {
        "variables": {"date_from": date_from, "date_to": date_to},
        "limit": LIMITE_FILAS,
    }

    try:
        respuesta = requests.post(url, headers=headers, json=cuerpo, timeout=TIMEOUT)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.exceptions.RequestException as exc:
        estado = getattr(getattr(exc, "response", None), "status_code", None)
        logger.error(
            "Error al ejecutar el endpoint PostHog %s (HTTP %s): %s",
            nombre,
            estado,
            exc,
        )
        raise RecuerdameAnalyticsError(MENSAJE_ERROR) from None
    except ValueError:
        logger.error("Respuesta no JSON del endpoint PostHog %s.", nombre)
        raise RecuerdameAnalyticsError(MENSAJE_ERROR) from None

    if isinstance(datos, dict) and datos.get("hasMore"):
        logger.warning("El endpoint %s tiene más de %s filas; resultado truncado.", nombre, LIMITE_FILAS)
    filas = _filas_como_dicts(datos)
    cache.set(clave_cache, filas, CACHE_SEGUNDOS)
    return filas


def _filas_como_dicts(datos):
    """Normaliza la respuesta (``results`` + ``columns``) a una lista de dicts."""
    if not isinstance(datos, dict):
        return []
    resultados = datos.get("results")
    if resultados is None:
        resultados = datos.get("result") or []
    columnas = datos.get("columns") or []
    filas = []
    for fila in resultados:
        if isinstance(fila, dict):
            filas.append(fila)
        elif isinstance(fila, (list, tuple)) and columnas:
            filas.append(dict(zip(columnas, fila)))
    return filas


# ---------------------------------------------------------------------------
# Utilidades de conversión
# ---------------------------------------------------------------------------


def _clave(texto):
    """Minúsculas, sin tildes, con guion bajo (para tolerar variantes de nombre)."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip().lower().replace(" ", "_").replace("-", "_")


def _numero(valor, defecto=0.0):
    try:
        if valor is None or valor == "":
            return defecto
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def _entero(valor):
    return int(round(_numero(valor)))


def _mediana(valores):
    valores = [v for v in valores if v is not None]
    return statistics.median(valores) if valores else 0


def formatear_duracion(segundos):
    segundos = int(round(_numero(segundos)))
    if segundos <= 0:
        return "–"
    minutos, seg = divmod(segundos, 60)
    horas, minutos = divmod(minutos, 60)
    if horas:
        return f"{horas} h {minutos} min"
    if minutos:
        return f"{minutos} min {seg} s"
    return f"{seg} s"


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------


def obtener_usuarios(date_from, date_to):
    """Lista de dicts (una fila por persona) del endpoint de usuarios."""
    return _ejecutar_endpoint(ENDPOINT_USUARIOS, date_from, date_to)


def buscar_usuario_por_email(usuarios, email):
    email = (email or "").strip().lower()
    for fila in usuarios:
        if str(fila.get("email") or "").strip().lower() == email:
            return fila
    return None


def detalle_usuario(fila):
    """Prepara la fila de una persona para la ficha de detalle."""
    vistas = [
        {"clave": clave, "etiqueta": etiqueta, "vistas": _entero(fila.get(f"vistas_{clave}"))}
        for clave, etiqueta in SECCIONES.items()
    ]
    rol = _clave(fila.get("rol_aproximado"))
    dispositivo = str(fila.get("dispositivo_principal") or "")
    return {
        "email": fila.get("email") or "",
        "nombre": fila.get("nombre") or "",
        "person_id": fila.get("person_id") or "",
        "dias_activos": _entero(fila.get("dias_activos")),
        "dias_ventana": _entero(fila.get("dias_ventana")),
        "adherencia": _adherencia_pct(fila),
        "sesiones": _entero(fila.get("sesiones")),
        "pageviews": _entero(fila.get("pageviews")),
        "duracion": formatear_duracion(fila.get("duracion_media_sesion_seg")),
        "interacciones_por_sesion": round(_numero(fila.get("autocapture_por_sesion")), 1),
        "secciones_distintas": _entero(fila.get("amplitud_secciones")),
        "dias_desde_ultima": fila.get("recencia_dias"),
        "rol": ROLES.get(rol, fila.get("rol_aproximado") or "–"),
        "rageclicks": _entero(fila.get("rageclicks")),
        "primera_actividad": fila.get("primera_actividad") or "–",
        "ultima_actividad": fila.get("ultima_actividad") or "–",
        "dispositivo": DISPOSITIVOS.get(dispositivo.lower(), dispositivo or "–"),
        "vistas_secciones": vistas,
    }


def _adherencia_pct(fila):
    """``adherencia`` llega como fracción 0-1 (días activos / días de la ventana)."""
    return round(_numero(fila.get("adherencia")) * 100, 1)


# ---------------------------------------------------------------------------
# Cohorte (dashboard)
# ---------------------------------------------------------------------------

def _dias_entre(date_from, date_to):
    desde = datetime.strptime(date_from, "%Y-%m-%d").date()
    hasta = datetime.strptime(date_to, "%Y-%m-%d").date()
    dias = (hasta - desde).days + 1
    return [(desde + timedelta(days=i)).isoformat() for i in range(max(dias, 0))]


def _por_serie(filas):
    series = {}
    for fila in filas:
        series.setdefault(_clave(fila.get("serie")), []).append(fila)
    return series


def _etiqueta_persona(fila):
    """Etiqueta legible para tooltips (nombre, correo o id corto)."""
    nombre = str(fila.get("nombre") or "").strip()
    email = str(fila.get("email") or "").strip()
    if nombre and email:
        return f"{nombre} ({email})"
    if nombre or email:
        return nombre or email
    person_id = str(fila.get("person_id") or "").strip()
    if person_id:
        return person_id[:8] + "…"
    return "Persona"


def _payload_analisis(usuarios):
    """Series por persona para gráficas exploratorias (scatter, box, roles)."""
    puntos = []
    por_rol = {}
    for fila in usuarios:
        rol_clave = _clave(fila.get("rol_aproximado")) or "sin_determinar"
        rol = ROLES.get(rol_clave, fila.get("rol_aproximado") or "Sin determinar")
        adherencia = _adherencia_pct(fila)
        duracion = _numero(fila.get("duracion_media_sesion_seg"))
        sesiones = _entero(fila.get("sesiones"))
        amplitud = _entero(fila.get("amplitud_secciones"))
        pageviews = _entero(fila.get("pageviews"))
        intensidad = round(_numero(fila.get("autocapture_por_sesion")), 1)
        punto = {
            "etiqueta": _etiqueta_persona(fila),
            "rol": rol,
            "adherencia": adherencia,
            "duracion_seg": duracion,
            "sesiones": sesiones,
            "amplitud": amplitud,
            "pageviews": pageviews,
            "intensidad": intensidad,
            "rageclicks": _entero(fila.get("rageclicks")),
            "recencia_dias": _entero(fila.get("recencia_dias")),
        }
        puntos.append(punto)
        por_rol.setdefault(rol, []).append(adherencia)

    return {
        "puntos": puntos,
        "adherencia_por_rol": {
            "labels": list(por_rol.keys()),
            "series": list(por_rol.values()),
        },
        "amplitud_mediana": round(_mediana([p["amplitud"] for p in puntos]), 1) if puntos else 0,
        "intensidad_mediana": round(
            _mediana([p["intensidad"] for p in puntos]), 1
        )
        if puntos
        else 0,
        "rageclicks_total": sum(p["rageclicks"] for p in puntos),
    }


def obtener_cohorte(date_from, date_to):
    """Datos listos para el dashboard: KPIs, series agregadas y análisis por persona.

    Personas y sesiones salen de la serie ``total``; las medianas y el scatter
    usan el endpoint de usuarios (misma fuente que el CSV).
    """
    series = _por_serie(_ejecutar_endpoint(ENDPOINT_COHORTE, date_from, date_to))
    usuarios = obtener_usuarios(date_from, date_to)
    analisis = _payload_analisis(usuarios)

    total = (series.get("total") or [{}])[0]
    personas = _entero(total.get("personas")) if total else len(usuarios)
    sesiones = _entero(total.get("sesiones")) if total else sum(_entero(u.get("sesiones")) for u in usuarios)

    # Los días sin actividad no vienen en la serie: se completan con cero.
    dau = {str(f.get("clave"))[:10]: _entero(f.get("personas")) for f in series.get("dau", [])}
    dias = _dias_entre(date_from, date_to)

    por_hora = {_entero(f.get("clave")): _entero(f.get("eventos")) for f in series.get("hora", [])}

    secciones = sorted(
        (
            (SECCIONES.get(_clave(f.get("clave")), str(f.get("clave"))), _entero(f.get("vistas")))
            for f in series.get("seccion", [])
        ),
        key=lambda par: -par[1],
    )
    dispositivos = [
        (DISPOSITIVOS.get(str(f.get("clave")).lower(), str(f.get("clave") or "Otro")), _entero(f.get("personas")))
        for f in series.get("dispositivo", [])
    ]

    return {
        "kpis": {
            "personas": personas,
            "adherencia_mediana": round(_mediana([_adherencia_pct(u) for u in usuarios]), 1),
            "duracion_mediana": formatear_duracion(
                _mediana([_numero(u.get("duracion_media_sesion_seg")) for u in usuarios])
            ),
            "sesiones": sesiones,
            "amplitud_mediana": analisis["amplitud_mediana"],
            "intensidad_mediana": analisis["intensidad_mediana"],
            "rageclicks_total": analisis["rageclicks_total"],
        },
        "actividad": {"labels": dias, "values": [dau.get(d, 0) for d in dias]},
        "secciones": {"labels": [e for e, _ in secciones], "values": [v for _, v in secciones]},
        "hora": {
            "labels": [f"{h:02d}:00" for h in range(24)],
            "values": [por_hora.get(h, 0) for h in range(24)],
        },
        "dispositivo": {"labels": [e for e, _ in dispositivos], "values": [v for _, v in dispositivos]},
        "analisis": analisis,
    }


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def _celda_segura(valor):
    """Evita inyección de fórmulas en Excel para textos que empiezan con = + - @."""
    if valor is None:
        return ""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@"):
        return "'" + valor
    return valor


def construir_tabla_csv(usuarios):
    """(encabezados, filas) con todas las personas. Columnas conocidas primero,
    en el orden definido arriba; las columnas extra del endpoint se conservan."""
    presentes = []
    for fila in usuarios:
        for columna in fila:
            if columna not in presentes:
                presentes.append(columna)
    conocidas = [c for c in COLUMNAS_USUARIOS if c in presentes]
    extras = [c for c in presentes if c not in COLUMNAS_USUARIOS]
    columnas = conocidas + extras

    encabezados = [COLUMNAS_USUARIOS.get(c, c) for c in columnas]
    filas = []
    for fila in usuarios:
        celdas = []
        for c in columnas:
            if c == "adherencia":
                celdas.append(_adherencia_pct(fila))
            elif c == "rol_aproximado":
                celdas.append(ROLES.get(_clave(fila.get(c)), fila.get(c) or ""))
            else:
                celdas.append(_celda_segura(fila.get(c)))
        filas.append(celdas)
    return encabezados, filas
