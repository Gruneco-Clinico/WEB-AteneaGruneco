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
    path("index/", views.index, name="index"),  # Página de inicio de Atenea
    path("login/", login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", profile_view, name="profile"),  # Perfil de usuario
    path(
        "contrasena/", views.cambiar_contrasena, name="cambiar_contrasena"
    ),  # Perfil de usuario
    # resgistro de pacientes
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
    # Tipos de isitas
    path("agregar-visita/", views.agregar_visita, name="agregar_visita"),
    path(
        "Tipovisita/eliminar/<int:id>/", views.eliminar_visita, name="eliminar_visita"
    ),
    path("editarVisita/<int:visita_id>/", views.editar_visita, name="editar_visita"),
    # visitas
    path("visita/<int:paciente_id>/", views.crear_visita, name="crear_visita"),
    path("eliminar-visita/<int:visita_id>/", views.eliminar_v, name="eliminar_v"),
    path("editar-visita/<int:visita_id>/", views.editar_v, name="editar_v"),
    # examenes
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
]
