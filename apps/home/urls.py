# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path
from apps.home import views
from .views import login_view, profile_view

urlpatterns = [
    # Páginas principales
    path("", views.home, name="home"),  # Página de inicio gruneco.com.co
    # path('ads/', views.ads, name='ads'),
    path("index/", views.index, name="index"),
    path(
        "estadisticas/", views.estadisticas, name="estadisticas"
    ),  # Página de estadísticas
    path("login/", login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", profile_view, name="profile"),  # Perfil de usuario
    path(
        "contrasena/", views.cambiar_contrasena, name="cambiar_contrasena"
    ),  # Perfil de usuario
    # Resgistro de pacientes
    path(
        "registro_demografico/", views.registro_demografico, name="registro_demografico"
    ),
    path("pacientes/", views.lista_pacientes, name="tables.html"),
    path(
        "paciente/<int:paciente_id>/", views.detalle_paciente, name="detalle_paciente"
    ),
    path(
        "paciente/<int:numero_documento>/eliminar/",
        views.eliminar_paciente,
        name="eliminar_paciente",
    ),
    path(
        "paciente/<int:numero_documento>/editar/",
        views.editar_paciente,
        name="editar_paciente",
    ),
    path("proyectos/", views.proyectos, name="proyectos"),
    path(
        "proyecto/<int:id>/eliminar/", views.eliminar_proyecto, name="eliminar_proyecto"
    ),
    # Tipos de visitas
    path("agregar-visita/", views.agregar_visita, name="agregar_visita"),
    path(
        "Tipovisita/eliminar/<int:id>/", views.eliminar_visita, name="eliminar_visita"
    ),
    path("editarVisita/<int:visita_id>/", views.editar_visita, name="editar_visita"),
    # Visitas
    path("visita/<int:paciente_id>/", views.crear_visita, name="crear_visita"),
    path("eliminar-visita/<int:visita_id>/", views.eliminar_v, name="eliminar_v"),
    path("editar-visita/<int:visita_id>/", views.editar_v, name="editar_v"),
    # Exámenes
    path(
        "examen/resultado/<int:visita_examen_id>/",
        views.ver_resultado_examen,
        name="ver_resultado_examen",
    ),
    path(
        "realizar_examen/<int:visita_id>/<int:examen_id>/<int:paciente_id>/",
        views.realizar_examen,
        name="realizar_examen",
    ),
    path(
        "examen_sueno_fisico/",
        views.guardar_examen_fisico_sueno,
        name="guardar_examen_sueno_fisico",
    ),
    path(
        "guardar_sueno_anamnesis/",
        views.guardar_sueno_anamnesis,
        name="guardar_examen_anamnesis",
    ),
    path("guardar_atenas/", views.guardar_atenas, name="guardar_atenas"),
    path("guardar_berlin/", views.guardar_berlin, name="guardar_berlin"),
    path(
        "guardar_examen_Epworth/",
        views.guardar_examen_Epworth,
        name="guardar_examen_Epworth",
    ),
    path("guardar_examen_ISI/", views.guardar_examen_ISI, name="guardar_examen_ISI"),
    path("guardar_examen_MEW/", views.guardar_examen_MEW, name="guardar_examen_MEW"),
    path(
        "guardar_examen_Pitsburg/",
        views.guardar_examen_Pitsburg,
        name="guardar_examen_Pitsburg",
    ),
    path(
        "guardar_examen_StopBang/",
        views.guardar_examen_StopBang,
        name="guardar_examen_StopBang",
    ),
    # Anosognosia
    path(
        "guardar_examen_Participante_EuroQoL/",
        views.guardar_examen_Participante_EuroQoL,
        name="guardar_examen_Participante_EuroQoL",
    ),
    path(
        "guardar_examen_Participante_EVA_EuroQoL/",
        views.guardar_examen_Participante_EVA_EuroQoL,
        name="guardar_examen_Participante_EVA_EuroQoL",
    ),
    path(
        "guardar_examen_Cuidador_NPI/",
        views.guardar_examen_Cuidador_NPI,
        name="guardar_examen_Cuidador_NPI",
    ),
    path(
        "guardar_examen_Cuidador_LawtonBrody/",
        views.guardar_examen_Cuidador_LawtonBrody,
        name="guardar_examen_Cuidador_LawtonBrody",
    ),
    path(
        "guardar_examen_Participante_Yesavage/",
        views.guardar_examen_Participante_Yesavage,
        name="guardar_examen_Participante_Yesavage",
    ),
    path(
        "guardar_examen_Cuidador_Zarit/",
        views.guardar_examen_Cuidador_Zarit,
        name="guardar_examen_Cuidador_Zarit",
    ),
    path(
        "guardar_examen_Participante_AQD/",
        views.guardar_examen_Participante_AQD,
        name="guardar_examen_Participante_AQD",
    ),
    path(
        "guardar_examen_Cuidador_AQD/",
        views.guardar_examen_Cuidador_AQD,
        name="guardar_examen_Cuidador_AQD",
    ),
    path(
        "guardar_examen_Participante_MoCA/",
        views.guardar_examen_Participante_MoCA,
        name="guardar_examen_Participante_MoCA",
    ),
    path(
        "guardar_examen_Cuidador_CDR/",
        views.guardar_examen_Cuidador_CDR,
        name="guardar_examen_Cuidador_CDR",
    ),
    path(
        "guardar_examen_Cuidador_RedLatSpanish/",
        views.guardar_examen_Cuidador_RedLatSpanish,
        name="guardar_examen_Cuidador_RedLatSpanish",
    ),
    path(
        "guardar_examen_Participante_CDR/",
        views.guardar_examen_Participante_CDR,
        name="guardar_examen_Participante_CDR",
    ),
    path(
        "guardar_examen_BettyFerrel/",
        views.guardar_examen_BettyFerrel,
        name="guardar_examen_BettyFerrel",
    ),
    path(
        "guardar_evaluacion_clinica_CDR/",
        views.guardar_evaluacion_clinica_CDR,
        name="guardar_evaluacion_clinica_CDR",
    ),
    path(
        "guardar_consentimiento_participante/",
        views.guardar_consentimiento_participante,
        name="guardar_consentimiento_participante",
    ),
    path(
        "guardar_consentimiento_cuidador/",
        views.guardar_consentimiento_cuidador,
        name="guardar_consentimiento_cuidador",
    ),
    path(
        "guardar_anamnesis_cuidador/",
        views.guardar_anamnesis_cuidador,
        name="guardar_anamnesis_cuidador",
    ),
    path(
        "guardar_anamnesis_participante/",
        views.guardar_anamnesis_participante,
        name="guardar_anamnesis_participante",
    ),
    # examanes generales
    path(
        "guardar_examen_analisis/",
        views.guardar_examen_analisis,
        name="guardar_examen_analisis",
    ),
    path(
        "guardar_examen_antecedentes/",
        views.guardar_examen_antecedentes,
        name="guardar_examen_antecedentes",
    ),
]
