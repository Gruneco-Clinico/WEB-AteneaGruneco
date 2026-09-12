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
    path(
        "examen/<int:visita_examen_id>/pdf/",
        views.generar_pdf_examen_generico,
        name="generar_pdf_examen_generico",
    ),
    path("index/", views.index, name="index"),
    path(
        "atenea_estadisticas/", views.atenea_estadisticas, name="atenea_estadisticas"
    ),  # Página de estadísticas
    path(
        "api/estadisticas-proyecto/",
        views.api_estadisticas_proyecto,
        name="api_estadisticas_proyecto",
    ),
    path(
        "api/estadisticas-evaluadores/",
        views.api_estadisticas_evaluadores,
        name="api_estadisticas_evaluadores",
    ),
    path(
        "api/dashboard-data/",
        views.api_dashboard_data,
        name="api_dashboard_data",
    ),
    path("login/", login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", profile_view, name="profile"),  # Perfil de usuario
    path("contrasena/", views.cambiar_contrasena, name="cambiar_contrasena"),
    # Perfil de usuario
    path("usuarios/", views.administrar_usuarios, name="administrar_usuarios"),
    # URLs públicas para agendamiento de citas
    path(
        "citas/agendar/",
        views.AgendarCitaPublicaView.as_view(),
        name="agendar_cita_publica",
    ),
    path(
        "api/disponibilidad-publica/",
        views.api_eventos_disponibilidad_publica,
        name="api_eventos_disponibilidad_publica",
    ),
    path("api/agendar-cita/", views.agendar_cita_ajax, name="agendar_cita_ajax"),
    # disponibilidad
    path(
        "disponibilidad/",
        views.gestionar_disponibilidad,
        name="gestionar_disponibilidad",
    ),
    path(
        "api/eventos-disponibilidad/",
        views.api_eventos_disponibilidad,
        name="api_eventos_disponibilidad",
    ),
    # Gestión de salas
    path(
        "salas/",
        views.gestionar_salas,
        name="gestionar_salas",
    ),
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
    # URLs públicas (sin autenticación)
    path(
        "registro-demografico/",
        views.formulario_demografico_externo,
        name="formulario_demografico_externo",
    ),
    path(
        "registro-exitoso/",
        views.confirmacion_registro_externo,
        name="confirmacion_registro_externo",
    ),
    path("consulta-examenes/", views.consulta_examenes, name="consulta_examenes"),
    path(
        "firma-consentimiento-publico/",
        views.firma_consentimiento_publico,
        name="firma_consentimiento_publico",
    ),
    # URLs públicas para exámenes
    path(
        "guardar-examen-publico-epworth/",
        views.guardar_examen_publico_epworth,
        name="guardar_examen_publico_epworth",
    ),
    path(
        "guardar-examen-publico-mew/",
        views.guardar_examen_publico_mew,
        name="guardar_examen_publico_mew",
    ),
    # En tu archivo urls.py, añade esta línea junto con las otras URLs:
    path(
        "guardar-examen-publico-pitsburg/",
        views.guardar_examen_publico_pitsburg,
        name="guardar_examen_publico_pitsburg",
    ),
    # PROYECTOS
    path("proyectos/", views.proyectos, name="proyectos"),
    path(
        "proyecto/<int:id>/eliminar/", views.eliminar_proyecto, name="eliminar_proyecto"
    ),
    path(
        "proyecto/<int:id>/editar/", views.editar_proyecto, name="editar_proyecto"
    ),
    path(
        "proyecto/<int:proyecto_id>/exportar-csv/",
        views.exportar_csv_proyecto,
        name="exportar_csv_proyecto",
    ),
    path(
        "paciente/<int:paciente_id>/proyecto/<int:proyecto_id>/quitar/",
        views.quitar_paciente_proyecto,
        name="quitar_paciente_proyecto",
    ),
    path(
        "paciente/<int:paciente_id>/proyecto/<int:proyecto_id>/enviar-link-firma/",
        views.enviar_link_firma_consentimiento,
        name="enviar_link_firma_consentimiento",
    ),
    # Visitas pendientes de firma
    path(
        "visitas-pendientes-firma/",
        views.visitas_pendientes_firma,
        name="visitas_pendientes_firma",
    ),
    # Tipos de visitas
    path("agregar-visita/", views.agregar_visita, name="agregar_visita"),
    path(
        "Tipovisita/eliminar/<int:id>/", views.eliminar_visita, name="eliminar_visita"
    ),
    path("editarVisita/<int:visita_id>/", views.editar_visita, name="editar_visita"),
    # Visitas
    path("visita/<int:paciente_id>/", views.crear_visita, name="crear_visita"),
    path(
        "visita/<int:paciente_id>/plan/",
        views.crear_plan_visitas,
        name="crear_plan_visitas",
    ),
    path(
        "visita/<int:visita_id>/abrir/",
        views.abrir_visita_programada,
        name="abrir_visita_programada",
    ),
    path(
        "serie/<int:serie_id>/cancelar/",
        views.cancelar_resto_serie_view,
        name="cancelar_resto_serie",
    ),
    path("eliminar-visita/<int:visita_id>/", views.eliminar_v, name="eliminar_v"),
    path("editar-visita/<int:visita_id>/", views.editar_v, name="editar_v"),
    path("firmar-visita/<int:visita_id>/", views.firmar_visita, name="firmar_visita"),
    path(
        "editar-notas-aclaratorias/<int:visita_id>/",
        views.editar_notas_aclaratorias,
        name="editar_notas_aclaratorias",
    ),
    path(
        "visita/<int:visita_id>/pdf/",
        views.generar_pdf_historia_clinica_visita,
        name="generar_pdf_historia_clinica_visita",
    ),
    path(
        "visita/<int:visita_id>/imprimir/",
        views.seleccionar_impresion_visita,
        name="seleccionar_impresion_visita",
    ),
    # Exámenes
    # path(
    #     "examen/resultado/<int:visita_examen_id>/",
    #     views.ver_resultado_examen,
    #     name="ver_resultado_examen",
    # ),
    path(
        "examenes/ver/<int:visita_examen_id>/",
        views.ver_resultado_examen,
        name="ver_resultado_examen",
    ),
    path(
        "realizar_examen/<int:visita_id>/<int:examen_id>/<int:paciente_id>/",
        views.realizar_examen,
        name="realizar_examen",
    ),
    path(
        "guardar_examen_builder/",
        views.guardar_examen_builder,
        name="guardar_examen_builder",
    ),
    path(
        "builder/examenes/",
        views.exam_builder_list,
        name="exam_builder_list",
    ),
    path(
        "builder/examenes/nuevo/",
        views.exam_builder_create,
        name="exam_builder_create",
    ),
    path(
        "builder/examenes/preview/",
        views.exam_builder_preview,
        name="exam_builder_preview",
    ),
    path(
        "builder/examenes/<int:pk>/",
        views.exam_builder_edit,
        name="exam_builder_edit",
    ),
    path(
        "builder/examenes/<int:pk>/publicar/",
        views.exam_builder_publish,
        name="exam_builder_publish",
    ),
    path(
        "builder/examenes/<int:pk>/eliminar/",
        views.exam_builder_delete,
        name="exam_builder_delete",
    ),
    path(
        "builder/tipo-visita/<int:pk>/examenes/",
        views.exam_builder_tipo_visita_edit,
        name="exam_builder_tipo_visita_edit",
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
    path(
        "guardar-cognitivo-anamnesis/",
        views.guardar_examen_cognitivo_anamnesis,
        name="guardar_cognitivo_anamnesis",
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
    path(
        "guardar_intervenciones/",
        views.guardar_intervenciones,
        name="guardar_intervenciones",
    ),
    path(
        "obtener_datos_sesion/<int:visita_id>/<int:examen_id>/<int:num_sesion>/",
        views.obtener_datos_sesion,
        name="obtener_datos_sesion",
    ),
    path(
        "resumen_sesiones/<int:visita_id>/<int:examen_id>/",
        views.resumen_sesiones,
        name="resumen_sesiones",
    ),
    # INTEGRACIÓN RECUÉRDAME
    path("estadisticas/", views.estadisticas, name="estadisticas"),
    # path("estadisticas_por_usuario/",
    #      views.estadisticas_por_usuario,
    #      name="estadisticas_por_usuario"),
    path(
        "listado_usuarios_recuerdame/",
        views.listado_usuarios_recuerdame,
        name="listado_usuarios_recuerdame",
    ),
    path(
        "estadisticas/usuarios/<str:email>/",
        views.estadisticas_usuario_detalle,
        name="estadisticas_usuario_detalle",
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
    path(
        "guardar_examen_medicamentos/",
        views.guardar_examen_medicamentos,
        name="guardar_examen_medicamentos",
    ),
    path(
        "guardar_examen_fisico/",
        views.guardar_examen_fisico,
        name="guardar_examen_fisico",
    ),
    path(
        "guardar_revision_sistemas/",
        views.guardar_revision_sistemas,
        name="guardar_revision_sistemas",
    ),
    path(
        "guardar_examen_neurologico/",
        views.guardar_examen_neurologico,
        name="guardar_examen_neurologico",
    ),
]
