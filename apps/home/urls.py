# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path
from apps.home import views
from .views import login_view, descargar_examen, profile_view

urlpatterns = [
    # Páginas principales
    path('', views.home, name='home'),  # Página de inicio gruneco.com.co
    #path('ads/', views.ads, name='ads'),
    
    path('index/', views.index, name='index'),  # Página de inicio de Atenea
    path('login/', login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),  # Perfil de usuario
    path('contrasena/', views.cambiar_contrasena, name='cambiar_contrasena'),  # Perfil de usuario

    #resgistro de pacientes 
    path('registro_demografico/', views.registro_demografico, name='registro_demografico'),
    path('pacientes/', views.lista_pacientes, name='tables.html'),
    path('paciente/<int:paciente_id>/', views.detalle_paciente, name='detalle_paciente'),
    path('paciente/<int:numero_documento>/eliminar/', views.eliminar_paciente, name='eliminar_paciente'),
    path('paciente/<int:numero_documento>/editar/', views.editar_paciente, name='editar_paciente'),
    path('eliminar-resultado-examen/<int:visita_id>/<int:examen_id>/<int:paciente_id>/', views.eliminar_resultado_examen, name='eliminar_resultado_examen'),

    # Exámenes médicos
    path('descargar-examen/<int:visita_examen_id>/', descargar_examen, name='descargar_examen'),
    path('examen/<int:visita_id>/<int:examen_id>/<int:paciente_id>/', views.realizar_examen, name='realizar_examen'),
    path('guardar-examen/cuestionarios/', views.guardar_examen_Sueño_Cuestionarios, name='guardar_Sueño_Cuestionarios'),
    path('guardar-examen/fisico-sueno/', views.guardar_examen_sueno_fisico, name='guardar_examen_sueno_fisico'),
    

    # Proyectos
    path('proyectos/', views.proyectos, name='proyectos'),
    path('proyecto/<int:id>/eliminar/', views.eliminar_proyecto, name='eliminar_proyecto'),
    
    #Historia clinica examenes 
    path('guardar-examen-general/', views.guardar_examen_general_revisionsistemas, name='guardar_examen'),
    path('guardar-examen-fisico/', views.guardar_examen_fisico, name='guardar_examen_fisico'),
    path('guardar-examen-antecedentes', views.guardar_examen_antecedentes, name='guardar_examen_antecedentes'),
    path('guardar-examen-medicamentos', views.guardar_examen_medicamentos, name='guardar_examen_medicamentos'), 
    path('guardar-examen-analisis', views.guardar_examen_analisis, name='guardar_examen_analisis'),
    path('guardar-examen-neurologico', views.guardar_examen_neurologico, name='guardar_examen_neurologico'),
    
    #Cuestioanrio de sueno
    path('guardar-examen/anamnesis/', views.guardar_examen_anamnesis, name='guardar_examen_anamnesis'),
    path('guardar-examen-Pitsburg', views.guardar_examen_Pitsburg, name='guardar_examen_Pitsburg'),
    path('guardar-examen-Epworth', views.guardar_examen_Epworth, name='guardar_examen_Epworth'),
    path('guardar-examen-Stop-Bang', views.guardar_examen_Stop_Bang, name='guardar_examen_Stop-Bang'),
    path('guardar-examen-MEW', views.guardar_examen_MEW, name='guardar_examen_MEW'),
    path('guardar-examen-Berlín', views.guardar_examen_Berlin, name='guardar_examen_Berlin'),
    path('guardar-examen-Atenas', views.guardar_examen_atenas, name='guardar_examen_atenas'),
    path('guardar-examen-ISI', views.guardar_examen_ISI, name='guardar_examen_ISI'),
    
    
    path('guardar-examen-cognitvio-anamnesis', views.guardar_examen_cognitivo_anamnesis, name='guardar_examen_cognitivo_anamnesis'),
    
    #proyectos
    path('proyectos/', views.proyectos, name='proyectos'),
    path('proyecto/eliminar/<int:id>/', views.eliminar_proyecto, name='eliminar_proyecto'),
    
    #Tipos de isitas
    path("agregar-visita/", views.agregar_visita, name="agregar_visita"),
    path('Tipovisita/eliminar/<int:id>/', views.eliminar_visita, name='eliminar_visita'),
    path('editarVisita/<int:visita_id>/', views.editar_visita, name='editar_visita'),
    
    #visitas
    path('visita/<int:paciente_id>/', views.crear_visita, name='crear_visita'),
    path('eliminar-visita/<int:visita_id>/', views.eliminar_v, name='eliminar_v'),
    path('editar-visita/<int:visita_id>/', views.editar_v, name='editar_v'),


    # Estadísticas
    path('estadisticas/', views.estadisticas, name='estadisticas'),
]
