# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .posthog_service import (
    get_posthog_events,
    get_insight_data,
)  # Integración RecuérdaMe
from django.conf import settings  # Integración RecuérdaMe
from django.http import JsonResponse, HttpResponseServerError  # Integración RecuérdaMe
from .models import InteractionMetric  # Integración RecuérdaMe
from datetime import datetime, date
from .models import *
from .forms import ProyectoForm, RegistroDemograficoForm
import json
from django.forms.models import model_to_dict

# from weasyprint import HTML
from django.contrib.auth import update_session_auth_hash


def is_superuser(user):
    return user.is_superuser


# vista principal #############################################################
def home(request):
    context = {"segment": "home"}
    html_template = loader.get_template("home/home-page.html")
    return HttpResponse(html_template.render(context, request))


# Ingreso y Salida #############################################################
@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("index")
        else:
            return render(
                request, "home/login.html", {"error": "Credenciales inválidas"}
            )
    return render(request, "home/login.html")


# Perfil #########################################################
@login_required
def profile_view(request):
    return render(request, "home/profile.html")


@login_required
def cambiar_contrasena(request):
    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password and confirm_password:
            if new_password == confirm_password:
                user = request.user
                user.set_password(new_password)  # Cambia la contraseña
                user.save()
                update_session_auth_hash(request, user)  # Mantiene la sesión activa
                messages.success(request, "¡Contraseña actualizada con éxito!")
                return render(request, "home/profile.html")
            else:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, "home/profile.html")
        else:
            messages.error(request, "Todos los campos son obligatorios.")

    return render(request, "home/profile.html")


# dashboard
@login_required(login_url="/login/")
def index(request):
    context = {"segment": "index"}
    html_template = loader.get_template("home/index.html")
    return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def atenea_estadisticas(request):
    context = {"segment": "atenea_estadisticas"}

    proyectos_a_buscar = [
        ("Anosognosia", "Anosognosia"),
        ("Proyecto Sueño", "Proyecto Sueño"),
        ("Envejecimiento", "Envejecimiento"),
    ]

    proyectos_info = []

    for term, label in proyectos_a_buscar:
        qs = Proyecto.objects.filter(nombre__icontains=term)

        participantes_count = 0
        exams_completed = 0
        clinical_stats = []
        genero_stats = []
        escolaridad_stats = []

        if qs.exists():
            # Participantes únicos
            patient_ids = qs.values_list("pacientes", flat=True)
            unique_patients = DatosDemograficos.objects.filter(id__in=patient_ids)

            participantes_count = unique_patients.count()

            # Distribución género
            if participantes_count > 0:
                hombres = unique_patients.filter(genero__iexact="M").count()
                mujeres = unique_patients.filter(genero__iexact="F").count()

                genero_stats = [
                    {
                        "label": "Género: Masculino",
                        "count": hombres,
                        "percent": round((hombres / participantes_count) * 100, 2),
                        "color": "primary",
                    },
                    {
                        "label": "Género: Femenino",
                        "count": mujeres,
                        "percent": round((mujeres / participantes_count) * 100, 2),
                        "color": "info",
                    },
                ]

            # Distribución escolaridad
            if participantes_count > 0:
                for nivel, color in [
                    ("primario", "warning"),
                    ("bachiller", "warning"),
                    ("universidad", "success"),
                    ("maestria", "danger"),
                    ("doctorado", "danger"),
                    ("especializacion", "danger"),
                ]:
                    count = unique_patients.filter(escolaridad__iexact=nivel).count()
                    escolaridad_stats.append(
                        {
                            "label": f"Escolaridad: {nivel}",
                            "count": count,
                            "percent": round((count / participantes_count) * 100, 2),
                            "color": color,
                        }
                    )

            # Exámenes completados
            exams_qs = VisitaExamen.objects.filter(
                visita__Tipo_visita__proyecto__in=qs,
                estado="completado",
            )
            exams_completed = exams_qs.count()

            # --- Distribución por rangos de edad ---
            rangos = [
                (18, 30, "18-30 años"),
                (31, 45, "31-45 años"),
                (46, 60, "46-60 años"),
                (61, 200, "60+ años"),  # límite alto grande
            ]

            for min_age, max_age, label_rango in rangos:
                count = unique_patients.filter(
                    edad__gte=min_age, edad__lte=max_age
                ).count()
                clinical_stats.append(
                    {
                        "rango": label_rango,
                        "count": count,
                    }
                )

        proyectos_info.append(
            {
                "term": term,
                "label": label,
                "participants": participantes_count,
                "exams_completed": exams_completed,
                "clinical_stats": clinical_stats,
                "demografia": genero_stats + escolaridad_stats,
            }
        )

    context["proyectos_info"] = proyectos_info
    return render(request, "home/statistics_atenea.html", context)


# pacientes
@login_required
def lista_pacientes(request):
    pacientes = DatosDemograficos.objects.all()
    return render(request, "home/tables.html", {"pacientes": pacientes})


@login_required
def registro_demografico(request):
    if request.method == "POST":
        try:
            datos = DatosDemograficos(
                # Datos obligatorios
                primer_nombre=request.POST["primer_nombre"],
                primer_apellido=request.POST["primer_apellido"],
                numero_documento=request.POST["numero_documento"],
                fecha_nacimiento=request.POST["fecha_nacimiento"],
                edad=request.POST["edad"],
                correo=request.POST["correo"],
                celular=request.POST["celular"],
                regimen=request.POST["regimen"],
                tipo_documento=request.POST["tipo_documento"],
                # Datos opcionales (se usa `.get()` para evitar errores si faltan)
                segundo_nombre=request.POST.get("segundo_nombre", ""),
                segundo_apellido=request.POST.get("segundo_apellido", ""),
                genero=request.POST.get("genero", ""),
                escolaridad=request.POST.get("escolaridad", ""),
                lateralidad=request.POST.get("lateralidad", ""),
                estado_civil=request.POST.get("estado_civil", ""),
                ocupacion=request.POST.get("ocupacion", ""),
                eps=request.POST.get("eps", ""),
                direccion=request.POST.get("direccion", ""),
                municipio_residencia=request.POST.get("municipio_residencia", ""),
                departamento_residencia=request.POST.get("departamento_residencia", ""),
                pais_residencia=request.POST.get("pais_residencia", ""),
                municipio_nacimiento=request.POST.get("municipio_nacimiento", ""),
                departamento_nacimiento=request.POST.get("departamento_nacimiento", ""),
                pais_nacimiento=request.POST.get("pais_nacimiento", ""),
                grupo_sanguineo=request.POST.get("grupo_sanguineo", ""),
                religion=request.POST.get("religion", ""),
            )
            datos.save()
            messages.success(request, "Datos demográficos guardados exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al guardar los datos: {str(e)}")

        return redirect("tables.html")

    if request.method == "GET":
        return render(request, "info_paciente/pacientForm.html")


@login_required
def eliminar_paciente(request, numero_documento):
    if request.method == "POST":
        paciente = get_object_or_404(
            DatosDemograficos, numero_documento=numero_documento
        )
        paciente.delete()
        messages.success(
            request, f"El paciente con documento {numero_documento} ha sido eliminado."
        )
        return redirect("tables.html")
    else:
        messages.error(request, "Método no permitido.")
        return redirect("tables.html")


@login_required
def editar_paciente(request, numero_documento):
    paciente = get_object_or_404(
        DatosDemograficos, numero_documento=numero_documento
    )  # Obtener el paciente por su ID

    if request.method == "POST":
        form = RegistroDemograficoForm(
            request.POST, instance=paciente
        )  # Cargar los datos del paciente
        if form.is_valid():
            form.save()  # Guardar los cambios
            pacientes = DatosDemograficos.objects.all()
            messages.success(request, "Datos demográficos editados exitosamente.")

            return render(request, "home/tables.html", {"pacientes": pacientes})

        else:
            messages.error(
                request,
                f"❌ Error en el formulario. Verifica los campos. {str(form.errors)}",
            )
            return render(request, "info_paciente/editPacientForm.html", {"form": form})
            # Para depuración en la consola

    # Redirigir a una página de detalle del paciente
    if request.method == "GET":
        form = RegistroDemograficoForm(
            instance=paciente
        )  # Cargar el formulario con los datos del paciente
        return render(request, "info_paciente/editPacientForm.html", {"form": form})


@login_required
def detalle_paciente(request, paciente_id):
    proyectos = Proyecto.objects.all()
    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    # Obtener los proyectos en los que el paciente ya está asignado
    proyectos_asociados = paciente.proyectos.all()
    # Obtener proyectos disponibles para asignación (excluye los que ya tiene)
    proyectos_disponibles = Proyecto.objects.exclude(
        id__in=proyectos_asociados.values_list("id", flat=True)
    )

    # Obtener las visitas con sus exámenes relacionados (optimización)
    visitas_paciente = Visita.objects.filter(paciente=paciente).prefetch_related(
        "visita_examenes__examen"
    )

    if request.method == "POST":
        proyecto_id = request.POST.get("proyecto_id")
        pacientes_ids = request.POST.get("paciente_id")
        paciente = DatosDemograficos.objects.get(id=pacientes_ids)
        proyecto = Proyecto.objects.get(id=proyecto_id)
        proyecto.pacientes.add(paciente)
        proyecto.save()

    return render(
        request,
        "info_paciente/pacient.html",
        {
            "paciente": paciente,
            "proyectos": proyectos,
            "proyectos_asociados": proyectos_asociados,
            "proyectos_disponibles": proyectos_disponibles,
            "visitas_paciente": visitas_paciente,
        },
    )


# visitas del paciente
@login_required
def crear_visita(request, paciente_id):
    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    proyectos_asociados = paciente.proyectos.all()

    # Obtener los proyectos en los que el paciente ya está asignado
    proyectos_disponibles = Proyecto.objects.exclude(
        id__in=proyectos_asociados.values_list("id", flat=True)
    )

    # Obtener los tipos de visita disponibles para estos proyectos
    tipo_visitas = TipoVisita.objects.filter(proyecto__in=proyectos_asociados)

    if request.method == "POST":
        tipo_visita_id = request.POST.get("tipo_visita")
        fecha = request.POST.get("fecha")
        evaluador = request.POST.get("evaluador")
        nombre = request.POST.get("nombre")

        # Capturar datos del acompañante
        acompanante_nombre = request.POST.get("acompanante_nombre")
        acompanante_relacion = request.POST.get("acompanante_relacion")
        acompanante_correo = request.POST.get("acompanante_correo")
        acompanante_telefono = request.POST.get("acompanante_telefono")

        tipo_visita = get_object_or_404(TipoVisita, id=tipo_visita_id)

        # Crear la visita y asignarla al paciente
        nueva_visita = Visita.objects.create(
            paciente=paciente,
            nombre=nombre,
            Tipo_visita=tipo_visita,
            fecha=fecha,
            evaluador=evaluador,
            acompanante_nombre=acompanante_nombre,
            acompanante_relacion=acompanante_relacion,
            acompanante_correo=acompanante_correo,
            acompanante_telefono=acompanante_telefono,
        )

        # Procesar los exámenes seleccionados
        examenes_seleccionados = request.POST.get("examenes_seleccionados")
        if examenes_seleccionados:
            try:
                lista_ids_examenes = json.loads(examenes_seleccionados)

                # Crear un registro VisitaExamen para cada examen seleccionado
                for examen_id in lista_ids_examenes:
                    examen = Examen.objects.get(id=examen_id)
                    VisitaExamen.objects.create(
                        visita=nueva_visita,
                        examen=examen,
                        # El campo resultado quedará como NULL
                        # Los resultados se agregarán en otra función
                    )

                # Mensaje de éxito
                messages.success(
                    request,
                    f"Visita creada con éxito con {len(lista_ids_examenes)} exámenes asociados.",
                )

            except json.JSONDecodeError as e:
                messages.error(request, "Error al procesar los exámenes seleccionados.")

            # Mensaje de éxito
            messages.success(
                request,
                f"Visita  creada con éxito con {len(lista_ids_examenes)} exámenes asociados.",
            )

        return redirect(
            "detalle_paciente", paciente_id=paciente.id
        )  # Redirige después de crear

    return render(
        request,
        "info_paciente/pacient.html",
        {
            "paciente": paciente,
            "proyectos_asociados": proyectos_asociados,
            "proyectos_disponibles": proyectos_disponibles,
            "tipo_visitas": tipo_visitas,
        },
    )


@login_required
def eliminar_v(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    paciente_id = visita.paciente.id  # Para redirigir después de eliminar

    visita.delete()
    messages.success(request, "Visita eliminada correctamente.")

    return redirect("detalle_paciente", paciente_id=paciente_id)


@login_required
def editar_v(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    paciente = visita.paciente
    tipo_visita = visita.Tipo_visita  # Tipo de visita actual
    # Obtener exámenes disponibles según el tipo de visita (vienen en JSONField)
    examenes_tipo_visita = [
        int(examen["id"]) for examen in tipo_visita.examenes
    ]  # Este es un JSONField con los exámenes permitidos

    examenes_actuales = VisitaExamen.objects.filter(visita=visita).values_list(
        "examen_id", flat=True
    )
    # Exámenes ya asociados
    examenes_disponibles = Examen.objects.filter(id__in=examenes_tipo_visita).exclude(
        id__in=examenes_actuales
    )

    if request.method == "POST":
        # Obtener datos del formulario
        visita.nombre = request.POST.get("nombre", visita.nombre)
        visita.fecha = request.POST.get("fecha", visita.fecha)
        visita.evaluador = request.POST.get("evaluador", visita.evaluador)

        # Datos del acompañante
        visita.acompanante_nombre = request.POST.get(
            "acompanante_nombre", visita.acompanante_nombre
        )
        visita.acompanante_relacion = request.POST.get(
            "acompanante_relacion", visita.acompanante_relacion
        )
        visita.acompanante_correo = request.POST.get(
            "acompanante_correo", visita.acompanante_correo
        )
        visita.acompanante_telefono = request.POST.get(
            "acompanante_telefono", visita.acompanante_telefono
        )

        # Guardar cambios en la visita
        visita.save()

        # Procesar los exámenes seleccionados
        examenes_seleccionados = request.POST.getlist("examenes_seleccionados")

        for examen_id in examenes_seleccionados:
            examen = Examen.objects.get(id=int(examen_id))  # Convertimos ID a entero
            if not VisitaExamen.objects.filter(visita=visita, examen=examen).exists():
                VisitaExamen.objects.create(visita=visita, examen=examen)

                messages.success(
                    request,
                    f"Visita actualizada con éxito con {len(examenes_seleccionados)} exámenes.",
                )
            else:
                messages.warning(request, "No se seleccionaron exámenes.")

        return redirect("detalle_paciente", paciente_id=paciente.id)
    return render(
        request,
        "info_paciente/editar_visita.html",
        {
            "visita": visita,
            "paciente": paciente,
            "examenes_actuales": examenes_actuales,
            "examenes_disponibles": examenes_disponibles,
        },
    )


# proyectos ############################################################
@login_required
@user_passes_test(is_superuser, login_url="/login/")
def proyectos(request):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect(
            "index"
        )  # Cambia 'home' por la vista a la que quieras redirigir

    proyectos = Proyecto.objects.all()
    examenes = Examen.objects.all()
    visitas = TipoVisita.objects.all()

    # Crear un diccionario para almacenar las visitas y exámenes por proyecto
    proyecto_data = {}
    for proyecto in proyectos:
        visitas_proyecto = visitas.filter(proyecto=proyecto)
        visitas_info = []
        for visita in visitas_proyecto:
            # Asegurar que los datos sean una lista de diccionarios
            examenes_data = (
                visita.examenes
                if isinstance(visita.examenes, list)
                else json.loads(visita.examenes)
            )

            # Extraer solo los IDs de los exámenes y convertirlos a enteros
            examenes_ids = [int(examen["id"]) for examen in examenes_data]

            # Buscar los nombres de los exámenes en la base de datos
            examenes_nombres = Examen.objects.filter(id__in=examenes_ids).values_list(
                "nombre", flat=True
            )

            visitas_info.append(
                {
                    "id": visita.id,
                    "nombre": visita.nombre,
                    "observaciones": visita.observaciones,
                    "examenes": examenes_nombres,
                }
            )
        proyecto_data[proyecto.id] = visitas_info

    context = {
        "proyectos": proyectos,
        "examenes": examenes,
        "visitas": visitas,
        "proyecto_data": proyecto_data,
    }

    if request.method == "POST":
        proyecto_form = ProyectoForm(request.POST)
        if proyecto_form.is_valid():
            proyecto_form.save()
            messages.success(request, "Proyecto creado correctamente.")

        return redirect("proyectos")

    return render(request, "home/proyectos.html", context)


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def eliminar_proyecto(request, id):
    if request.method == "POST":
        proyecto = get_object_or_404(
            Proyecto, id=id
        )  # Asegúrate de que Proyecto es el nombre del modelo de tus proyectos
        proyecto.delete()
        messages.success(request, f"El proyecto con ID {id} ha sido eliminado.")
        return redirect("proyectos")  # Redirige a la lista de proyectos, por ejemplo
    else:
        messages.error(request, "Método no permitido.")
        return redirect(
            "proyectos"
        )  # Redirige a la lista de proyectos si no es un POST


@login_required
@user_passes_test(is_superuser, login_url="/login/")
# tipos de visita visitas
def agregar_visita(request):
    proyectos = Proyecto.objects.all()
    examenes = Examen.objects.all()
    visitas = TipoVisita.objects.all()

    # Crear un diccionario para almacenar las visitas y exámenes por proyecto
    proyecto_data = {}
    for proyecto in proyectos:
        visitas_proyecto = visitas.filter(proyecto=proyecto)
        visitas_info = []
        for visita in visitas_proyecto:
            # Asegurar que los datos sean una lista de diccionarios
            examenes_data = (
                visita.examenes
                if isinstance(visita.examenes, list)
                else json.loads(visita.examenes)
            )

            # Extraer solo los IDs de los exámenes y convertirlos a enteros
            examenes_ids = [int(examen["id"]) for examen in examenes_data]

            # Buscar los nombres de los exámenes en la base de datos
            examenes_nombres = Examen.objects.filter(id__in=examenes_ids).values_list(
                "nombre", flat=True
            )
            visitas_info.append(
                {
                    "id": visita.id,
                    "nombre": visita.nombre,
                    "observaciones": visita.observaciones,
                    "examenes": examenes_nombres,
                }
            )
        proyecto_data[proyecto.id] = visitas_info

    context = {
        "proyectos": proyectos,
        "examenes": examenes,
        "visitas": visitas,
        "proyecto_data": proyecto_data,
    }

    if request.method == "POST":
        proyecto_id = request.POST.get("proyecto_id")
        nombres = request.POST.getlist("nombre_visita[]")  # Varias visitas
        observaciones_list = request.POST.getlist("observaciones[]")

        # Recibir el JSON desde el formulario y decodificarlo
        examenes_json = request.POST.get("examenes_json", "[]")
        examenes_lista = json.loads(examenes_json)  # Convertir a lista de diccionarios

        for i in range(len(nombres)):  # Crear una visita por cada nombre recibido
            TipoVisita.objects.create(
                proyecto_id=proyecto_id,
                nombre=nombres[i],
                observaciones=observaciones_list[i],
                examenes=examenes_lista,  # Guardar la lista completa de exámenes como JSON
            )

        return redirect("proyectos")

    return render(request, "home/proyectos.html", context)


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def eliminar_visita(request, id):
    # Obtener la visita o devolver un error 404 si no existe
    visita = get_object_or_404(TipoVisita, id=id)

    if request.method == "POST":
        # Luego, eliminar la visita
        visita.delete()

        # Mensaje de confirmación
        messages.success(request, "La visita ha sido eliminada correctamente.")

        return redirect(
            "proyectos"
        )  # Redirigir a la lista de proyectos o donde corresponda

    return redirect("proyectos")


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def editar_visita(request, visita_id):
    visita = get_object_or_404(TipoVisita, id=visita_id)

    if request.method == "POST":
        # Procesar el formulario de edición
        proyecto_id = request.POST.get("proyecto_id")
        nombre_visita = request.POST.get("nombre_visita")
        observaciones = request.POST.get("observaciones")
        examenes_seleccionados_ids = request.POST.getlist("examenes")

        # Actualizar los datos básicos de la visita
        visita.proyecto_id = proyecto_id
        visita.nombre = nombre_visita
        visita.observaciones = observaciones

        # Obtener los exámenes existentes (si los hay)
        examenes_existentes = visita.examenes if visita.examenes else []

        # Obtener los exámenes seleccionados por sus IDs
        examenes_seleccionados = Examen.objects.filter(
            id__in=examenes_seleccionados_ids
        )

        # Crear un diccionario de exámenes existentes para evitar duplicados
        examenes_dict = {examen["id"]: examen for examen in examenes_existentes}

        # Agregar los nuevos exámenes seleccionados
        for examen in examenes_seleccionados:
            if str(examen.id) not in examenes_dict:
                examenes_dict[str(examen.id)] = {
                    "id": examen.id,
                    "nombre": examen.nombre,
                }

        # Convertir el diccionario de vuelta a lista
        examenes_actualizados = list(examenes_dict.values())

        # Guardar los exámenes como JSON
        visita.examenes = examenes_actualizados
        visita.save()

        messages.success(request, "Visita actualizada correctamente.")
        return redirect("proyectos")


# exámenes #######################
@login_required
def realizar_examen(request, visita_id, examen_id, paciente_id):
    # Diccionario de configuración de exámenes
    exam_config = {
        3: {
            "template": "examenes_general/General_ExamenFísico.html",
            "model": ExamenFisicoResult,
        },
        4: {
            "template": "examenes_general/General_RevisiónSistemas.html",
            "model": RevisionSistemasResult,
        },
        5: {
            "template": "examenes_general/General_Antecedentes.html",
            "model": AntecedentesResult,
        },
        7: {
            "template": "examenes_general/General_Análisis.html",
            "model": AnalisisGeneralResult,
        },
        8: {
            "template": "examenes_general/General_Medicamentos.html",
            "model": MedicamentosResult,
        },
        9: {
            "template": "examenes_general/General_ExamenNeurológico.html",
            "model": ExamenNeurologicoResult,
        },
        10: {
            "template": "examenes_sueno/Sueno_anamnesis.html",
            "model": SuenoAnamnesisResult,
        },
        11: {"template": "examenes_sueno/Sueño_Cuestionarios.html", "model": None},
        12: {
            "template": "examenes_sueno/Sueño_ExamenFisico.html",
            "model": SuenoFisicoResult,
        },
        13: {
            "template": "examenes_sueno/sueno_Pitsburg.html",
            "model": PittsburghResult,
        },
        14: {"template": "examenes_sueno/sueno_Epworth.html", "model": EpworthResult},
        15: {
            "template": "examenes_sueno/sueno_Stop_Bang.html",
            "model": StopBangResult,
        },
        16: {"template": "examenes_sueno/sueno_MEW.html", "model": MEWResult},
        17: {"template": "examenes_sueno/sueno_Berlín.html", "model": BerlinResult},
        18: {"template": "examenes_sueno/sueno_atenas.html", "model": AtenasResult},
        19: {"template": "examenes_sueno/sueno_ISI.html", "model": ISIResult},
        21: {
            "template": "examenes_anosognosia/Anosognosia_Participante_EuroQoL.html",
            "model": EuroQol5D5LResult,
        },
        22: {
            "template": "examenes_anosognosia/Anosognosia_Participante_EVA_EuroQoL.html",
            "model": EuroQolEVASaludResult,
        },
        23: {
            "template": "examenes_anosognosia/Anosognosia_Participante_Yesavage.html",
            "model": ParticipanteYesavageResult,
        },
        24: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_NPI.html",
            "model": CuidadorNPIResult,
        },
        25: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_LawtonBrody.html",
            "model": LawtonBrodyResult,
        },
        26: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_CalidadVida_BettyFerrel.html",
            "model": BettyFerrelResult,
        },
        27: {
            "template": "examenes_anosognosia/Anosognosia_Participante_MoCA.html",
            "model": MoCAResult,
        },
        28: {
            "template": "examenes_anosognosia/Anosognosia_Participante_AdherenciaTerapeutica.html",
            "model": AdherenciaTerapeuticaResult,
        },
        29: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_EscalaZarit.html",
            "model": ZaritResult,
        },
        30: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_AQD.html",
            "model": AQDCuidadorResult,
        },
        31: {
            "template": "examenes_anosognosia/Anosognosia_Participante_AQD.html",
            "model": AQDParticipanteResult,
        },
        32: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_RedLatSpanish.html",
            "model": RedLatSpanishResult,
        },
        33: {
            "template": "examenes_anosognosia/Anosognosia_Cuidador_CDR.html",
            "model": CDRCuidadorResult,
        },
        34: {
            "template": "examenes_anosognosia/Anosognosia_Participante_CDR.html",
            "model": CDRParticipanteResult,
        },
        35: {
            "template": "examenes_anosognosia/CDR_Evaluacion_Clinica.html",
            "model": PuntajeCDRResult,
        },
        36: {
            "template": "examenes_anosognosia/Consentimiento_Informado_Participante.html",
            "model": ConsentimientoInformadoParticipanteResult,
        },
        37: {
            "template": "examenes_anosognosia/Consentimiento_Informado_Cuidador.html",
            "model": ConsentimientoInformadoCuidadorResult,
        },
        38: {
            "template": "examenes_anosognosia/Anamnesis_Cuidador_ANG.html",
            "model": AnamnesisCuidadorResult,
        },
        39: {
            "template": "examenes_anosognosia/Anamnesis_Participante_ANG.html",
            "model": AnamnesisParticipanteResult,
        },
        40: {
            "template": "examenes_anosognosia/SeguimientoIntervenciones_ANG.html",
            "model": SeguimientoIntervencionesResult,
        },
    }

    config = exam_config.get(int(examen_id))
    if not config:
        messages.error(request, "Examen no encontrado")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    # Obtener datos existentes
    datos_examen = None
    visita_examen_obj = None
    modo_edicion = False

    try:
        visita_examen_obj = VisitaExamen.objects.get(
            visita_id=visita_id, examen_id=examen_id
        )

        if config["model"] and visita_examen_obj.esta_realizado:
            resultado = visita_examen_obj.get_resultado_instance()
            if resultado and isinstance(resultado, config["model"]):
                # ===================================================
                # CASO ESPECIAL: ANAMNESIS DE SUEÑO (ID 10)
                # ===================================================
                if int(examen_id) == 10 and isinstance(resultado, SuenoAnamnesisResult):
                    # Obtener datos básicos del modelo principal
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)

                    # Obtener relaciones hijas con prefetch para optimización
                    anamnesis = SuenoAnamnesisResult.objects.prefetch_related(
                        "sustancias",
                        "medicamentos",
                        "pantallas",
                        "actividades_en_cama",
                        "actividades_fisicas",
                        "sintomas_suenos",
                        "sintomas_diurno",
                        "tipos_queja_detalle",
                    ).get(id=resultado.id)

                    # Agregar las relaciones al diccionario de datos
                    datos_examen["sustancias"] = list(
                        anamnesis.sustancias.values(
                            "tipo", "cantidad", "frecuencia", "tiempo", "observaciones"
                        )
                    )

                    datos_examen["medicamentos"] = list(
                        anamnesis.medicamentos.values(
                            "nombre",
                            "dosis",
                            "presentacion",
                            "veces_dia",
                            "frecuencia",
                            "tiempo",
                            "observaciones",
                        )
                    )

                    datos_examen["pantallas"] = list(
                        anamnesis.pantallas.values(
                            "tipo", "frecuencia", "tiempo_antes_dormir"
                        )
                    )

                    datos_examen["actividades_en_cama"] = list(
                        anamnesis.actividades_en_cama.values(
                            "tipo", "frecuencia", "observaciones"
                        )
                    )

                    datos_examen["actividades_fisicas"] = list(
                        anamnesis.actividades_fisicas.values(
                            "tipo",
                            "otro_texto",
                            "intensidad",
                            "frecuencia",
                            "observaciones",
                        )
                    )

                    datos_examen["sintomas_suenos"] = list(
                        anamnesis.sintomas_suenos.values(
                            "tipo",
                            "cuando_inicio",
                            "evolucion",
                            "frecuencia",
                            "gravedad",
                            "observaciones",
                        )
                    )

                    datos_examen["sintomas_diurnos"] = list(
                        anamnesis.sintomas_diurno.values(
                            "tipo",
                            "cuando_inicio",
                            "evolucion",
                            "frecuencia",
                            "gravedad",
                            "observaciones",
                        )
                    )

                    datos_examen["tipos_queja"] = list(
                        anamnesis.tipos_queja_detalle.values(
                            "nombre", "inicio", "evolucion", "frecuencia", "gravedad"
                        )
                    )

                    modo_edicion = True

                # ===================================================
                # CASO ESPECIAL: ANÁLISIS GENERAL (ID 7)
                # ===================================================
                elif int(examen_id) == 7 and isinstance(
                    resultado, AnalisisGeneralResult
                ):
                    # Obtener datos básicos del modelo principal
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)

                    # Obtener relaciones hijas con prefetch para optimización
                    analisis = AnalisisGeneralResult.objects.prefetch_related(
                        "diagnosticos_cie10",
                        "diagnosticos_dsmv",
                        "diagnosticos_icsd3",
                        "diagnosticos_no_clasificados",
                    ).get(id=resultado.id)

                    # Agregar las relaciones al diccionario de datos
                    datos_examen["diagnosticos_cie10"] = list(
                        analisis.diagnosticos_cie10.values(
                            "codigo",
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    datos_examen["diagnosticos_dsmv"] = list(
                        analisis.diagnosticos_dsmv.values(
                            "codigo",
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    datos_examen["diagnosticos_icsd3"] = list(
                        analisis.diagnosticos_icsd3.values(
                            "codigo",
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    datos_examen["diagnosticos_no_clasificados"] = list(
                        analisis.diagnosticos_no_clasificados.values(
                            "diagnostico",
                            "confirmado_nuevo",
                            "confirmado_antiguo",
                            "en_estudio",
                            "orden",
                        )
                    )

                    modo_edicion = True

                else:
                    # ===================================================
                    # CASO GENERAL: OTROS EXÁMENES
                    # ===================================================
                    datos_examen = model_to_dict(resultado)
                    datos_examen.pop("id", None)
                    datos_examen.pop("visita_examen", None)
                    modo_edicion = True

            # CASO ESPECIAL: ANTECEDENTES (ID 5) - FUERA DEL IF ANTERIOR
            # ===================================================
            elif int(examen_id) == 5:
                # Para antecedentes, verificar si existe un AntecedentesVisitaLink
                try:
                    antecedentes_link = AntecedentesVisitaLink.objects.get(
                        visita_examen=visita_examen_obj
                    )
                    antecedentes_result = antecedentes_link.antecedentes_result

                    if antecedentes_result:
                        # Obtener datos básicos del modelo principal
                        datos_examen = model_to_dict(antecedentes_result)
                        datos_examen.pop("id", None)
                        datos_examen.pop("paciente", None)

                        # Obtener relaciones hijas con prefetch para optimización
                        antecedentes = AntecedentesResult.objects.prefetch_related(
                            "antecedentes_patologicos",
                            "antecedentes_quirurgicos",
                            "antecedentes_farmacologicos",
                            "antecedentes_toxicos",
                            "antecedentes_familiares",
                            "antecedentes_alergicos",
                            "antecedentes_traumaticos",
                            "antecedentes_gineco",
                            "antecedentes_epidemiologicos",
                            "antecedentes_ets",
                            "antecedentes_hospitalizaciones",
                            "antecedentes_inmunizaciones",
                            "antecedentes_transfusionales",
                        ).get(id=antecedentes_result.id)

                        # Agregar las relaciones al diccionario de datos
                        datos_examen["patologicos"] = list(
                            antecedentes.antecedentes_patologicos.values(
                                "tipo_patologia",
                                "descripcion_otros",
                                "fecha_inicio",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["quirurgicos"] = list(
                            antecedentes.antecedentes_quirurgicos.values(
                                "descripcion",
                                "fecha_intervencion",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["farmacologicos"] = list(
                            antecedentes.antecedentes_farmacologicos.values(
                                "descripcion",
                                "fecha_inicio",
                                "recibio_tratamiento",
                                "detalle_tratamiento",
                                "tuvo_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["toxicos"] = list(
                            antecedentes.antecedentes_toxicos.values(
                                "tipos_toxico",
                                "descripcion_otros",
                                "fecha_inicio",
                                "ha_recibido_tratamiento",
                                "detalle_tratamiento",
                                "tiene_complicaciones",
                                "detalle_complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["familiares"] = list(
                            antecedentes.antecedentes_familiares.values(
                                "tipo_antecedente", "parentesco", "observaciones"
                            )
                        )

                        datos_examen["alergicos"] = list(
                            antecedentes.antecedentes_alergicos.values(
                                "descripcion",
                                "fecha_inicio",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["traumaticos"] = list(
                            antecedentes.antecedentes_traumaticos.values(
                                "descripcion",
                                "fecha_inicio",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "activo",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        # Gineco-obstétricos (OneToOne)
                        if (
                            hasattr(antecedentes, "antecedentes_gineco")
                            and antecedentes.antecedentes_gineco
                        ):
                            gineco_data = model_to_dict(
                                antecedentes.antecedentes_gineco
                            )
                            gineco_data.pop("id", None)
                            gineco_data.pop("antecedente_result", None)
                            datos_examen["gineco_obstetricos"] = gineco_data
                        else:
                            datos_examen["gineco_obstetricos"] = {}

                        datos_examen["epidemiologicos"] = list(
                            antecedentes.antecedentes_epidemiologicos.values(
                                "tipo_antecedente",
                                "fecha_inicio",
                                "tratamiento_detalle",
                                "complicaciones_asociadas",
                                "detallar_complicaciones",
                                "activo_actualmente",
                                "fecha_finalizacion",
                                "observaciones",
                            )
                        )

                        datos_examen["ets"] = list(
                            antecedentes.antecedentes_ets.values(
                                "tipo_ets",
                                "fecha_diagnostico",
                                "tratamiento_recibido",
                                "detalle_tratamiento",
                                "complicaciones",
                                "detalle_complicaciones",
                                "curado",
                                "fecha_curacion",
                                "observaciones",
                            )
                        )

                        datos_examen["hospitalizaciones"] = list(
                            antecedentes.antecedentes_hospitalizaciones.values(
                                "motivo_hospitalizacion",
                                "fecha_ingreso",
                                "fecha_egreso",
                                "duracion",
                                "institucion",
                                "observaciones",
                            )
                        )

                        datos_examen["inmunizaciones"] = list(
                            antecedentes.antecedentes_inmunizaciones.values(
                                "nombre_vacuna",
                                "fecha_aplicacion",
                                "dosis_numero",
                                "observaciones",
                            )
                        )

                        datos_examen["transfusionales"] = list(
                            antecedentes.antecedentes_transfusionales.values(
                                "motivo_transfusion",
                                "fecha_transfusion",
                                "tipo_componente",
                                "cantidad_unidades",
                                "tuvo_reacciones",
                                "detalle_reacciones",
                                "observaciones",
                            )
                        )

                        modo_edicion = True

                except AntecedentesVisitaLink.DoesNotExist:
                    # No hay antecedentes previos para esta visita
                    pass

    except VisitaExamen.DoesNotExist:
        messages.error(request, "Visita-examen no encontrada")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    return render(
        request,
        config["template"],
        {
            "visita_examen": visita_id,
            "paciente_id": paciente_id,
            "examen_id": examen_id,
            "datos_examen": datos_examen,
            "modo_edicion": modo_edicion,
            "visita_examen_obj": visita_examen_obj,
        },
    )


@login_required
def ver_resultado_examen(request, visita_examen_id):
    """Vista genérica para mostrar resultados de cualquier examen"""
    visita_examen = get_object_or_404(VisitaExamen, id=visita_examen_id)

    # Verificar que el examen esté completado
    if not visita_examen.esta_realizado:
        messages.error(request, "Este examen aún no ha sido completado.")
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )

    # Obtener el resultado específico del examen
    resultado = visita_examen.get_resultado_instance()

    if not resultado:
        messages.error(request, "No se encontraron resultados para este examen.")
        return redirect(
            "detalle_paciente", paciente_id=visita_examen.visita.paciente.id
        )

    # Convertir el resultado a diccionario para el template
    datos_resultado = {}
    for field in resultado._meta.fields:
        if field.name != "visita_examen":  # Excluir la relación
            valor = getattr(resultado, field.name)
            datos_resultado[field.verbose_name or field.name] = valor

    # Determinar el template específico basado en el tipo de examen
    template_mapping = {
        "SuenoFisicoResult": "examenes_resultados/resultado_sueno_fisico.html",
        "AtenasResult": "examenes_resultados/resultado_atenas.html",
        "PittsburghResult": "examenes_resultados/resultado_pittsburgh.html",
        "EpworthResult": "examenes_resultados/resultado_epworth.html",
        "LawtonBrodyResult": "examenes_resultados/resultado_lawtonbrody.html",
        "CuidadorNPIResult": "examenes_resultados/resultado_cuidadornpi.html",
        "EuroQol5D5LResult": "examenes_resultados/resultado_euroqol.html",
        "EuroQolEVASaludResult": "examenes_resultados/resultado_evasaludeuroqol.html",
        "MoCAResult": "examenes_resultados/resultado_moca.html",
        "ParticipanteYesavageResult": "examenes_resultados/resultado_yesavage.html",
        "ZaritResult": "examenes_resultados/resultado_zarit.html",
        "AQDCuidadorResult": "examenes_resultados/resultado_aqdcuidador.html",
        "AQDParticipanteResult": "examenes_resultados/resultado_aqdparticipante.html",
        "CDRCuidadorResult": "examenes_resultados/resultado_cdrcuidador.html",
        "CDRParticipanteResult": "examenes_resultados/resultado_cdrparticipante.html",
        "RedLatSpanishResult": "examenes_resultados/resultado_redlatspanish.html",
        "AdherenciaTerapeuticaResult": "examenes_resultados/resultado_adherenciaterapeutica.html",
        "BettyFerrelResult": "examenes_resultados/resultado_bettyferrel.html",
        "PuntajeCDRResult": "examenes_resultados/resultado_puntajeCDR.html",
        "ConsentimientoInformadoParticipanteResult": "examenes_resultados/resultado_consentimientoinformadoparticipante.html",
        "ConsentimientoInformadoCuidadorResult": "examenes_resultados/resultado_consentimientoinformadocuidador.html",
        "AnamnesisCuidadorResult": "examenes_resultados/resultado_anamnesiscuidador.html",
        "AnamnesisParticipanteResult": "examenes_resultados/resultado_anamnesisparticipante.html",
        "SeguimientoIntervencionesResult": "examenes_resultados/resultado_seguimientointervenciones.html",
        # Agregar más según tus exámenes
    }

    tipo_resultado = resultado.__class__.__name__
    template = template_mapping.get(
        tipo_resultado, "examenes_resultados/resultado_generico.html"
    )

    return render(
        request,
        template,
        {
            "visita_examen": visita_examen,
            "resultado": resultado,
            "datos_resultado": datos_resultado,
            "paciente": visita_examen.visita.paciente,
        },
    )


# examenes sueno
@login_required
def guardar_examen_fisico_sueno(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # CAMBIO: Usar el nuevo método para marcar como iniciado
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Crear o actualizar el resultado del examen físico de sueño
            sueno_fisico, created = SuenoFisicoResult.objects.get_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Medidas antropométricas - nombres comunes en templates
                    "peso": request.POST.get("peso")
                    or request.POST.get("weight")
                    or None,
                    "talla": request.POST.get("talla")
                    or request.POST.get("height")
                    or None,
                    "imc": request.POST.get("imc") or request.POST.get("bmi") or None,
                    "rango_imc": request.POST.get("rango_imc")
                    or request.POST.get("bmi_range")
                    or "",
                    "circunferencia_cuello": request.POST.get("circunferencia_cuello")
                    or request.POST.get("neck_circumference")
                    or None,
                    "perimetro_abdominal": request.POST.get("perimetro_abdominal")
                    or request.POST.get("abdominal_perimeter")
                    or None,
                    # Examen nasal
                    "simetria_narinas": request.POST.get("simetria_narinas")
                    or request.POST.get("nostril_symmetry")
                    or "",
                    "tipo_narina": request.POST.get("tipo_narina")
                    or request.POST.get("nostril_type")
                    or "",
                    "desviacion_septo": request.POST.get("desviacion_septo")
                    or request.POST.get("septum_deviation")
                    or "",
                    "hipertrofia_cornetes": request.POST.get("hipertrofia_cornetes")
                    or request.POST.get("turbinate_hypertrophy")
                    or "",
                    "grado": request.POST.get("grado")
                    or request.POST.get("grade")
                    or "",
                    # Examen orofaríngeo
                    "hipertrofia_uvula": request.POST.get("hipertrofia_uvula")
                    or request.POST.get("uvula_hypertrophy")
                    or "",
                    "biotipo": request.POST.get("biotipo")
                    or request.POST.get("biotype")
                    or "",
                    "mallampati": request.POST.get("mallampati")
                    or request.POST.get("mallampati_score")
                    or "",
                    "amigdalas": request.POST.get("amigdalas")
                    or request.POST.get("tonsils")
                    or "",
                    "tipo_mordida": request.POST.get("tipo_mordida")
                    or request.POST.get("bite_type")
                    or "",
                    # Otros
                    "alteracion_craneo": request.POST.get("alteracion_craneo")
                    or request.POST.get("cranial_alteration")
                    or "",
                },
            )

            # Si no es nuevo, actualizar los campos
            if not created:
                sueno_fisico.peso = (
                    request.POST.get("peso") or request.POST.get("weight") or None
                )
                sueno_fisico.talla = (
                    request.POST.get("talla") or request.POST.get("height") or None
                )
                sueno_fisico.imc = (
                    request.POST.get("imc") or request.POST.get("bmi") or None
                )
                sueno_fisico.rango_imc = (
                    request.POST.get("rango_imc") or request.POST.get("bmi_range") or ""
                )
                sueno_fisico.circunferencia_cuello = (
                    request.POST.get("circunferencia_cuello")
                    or request.POST.get("neck_circumference")
                    or None
                )
                sueno_fisico.perimetro_abdominal = (
                    request.POST.get("perimetro_abdominal")
                    or request.POST.get("abdominal_perimeter")
                    or None
                )
                sueno_fisico.simetria_narinas = (
                    request.POST.get("simetria_narinas")
                    or request.POST.get("nostril_symmetry")
                    or ""
                )
                sueno_fisico.tipo_narina = (
                    request.POST.get("tipo_narina")
                    or request.POST.get("nostril_type")
                    or ""
                )
                sueno_fisico.desviacion_septo = (
                    request.POST.get("desviacion_septo")
                    or request.POST.get("septum_deviation")
                    or ""
                )
                sueno_fisico.hipertrofia_cornetes = (
                    request.POST.get("hipertrofia_cornetes")
                    or request.POST.get("turbinate_hypertrophy")
                    or ""
                )
                sueno_fisico.grado = (
                    request.POST.get("grado") or request.POST.get("grade") or ""
                )
                sueno_fisico.hipertrofia_uvula = (
                    request.POST.get("hipertrofia_uvula")
                    or request.POST.get("uvula_hypertrophy")
                    or ""
                )
                sueno_fisico.biotipo = (
                    request.POST.get("biotipo") or request.POST.get("biotype") or ""
                )
                sueno_fisico.mallampati = (
                    request.POST.get("mallampati")
                    or request.POST.get("mallampati_score")
                    or ""
                )
                sueno_fisico.amigdalas = (
                    request.POST.get("amigdalas") or request.POST.get("tonsils") or ""
                )
                sueno_fisico.tipo_mordida = (
                    request.POST.get("tipo_mordida")
                    or request.POST.get("bite_type")
                    or ""
                )
                sueno_fisico.alteracion_craneo = (
                    request.POST.get("alteracion_craneo")
                    or request.POST.get("cranial_alteration")
                    or ""
                )
                sueno_fisico.save()

            # CAMBIO: Marcar el examen como completado usando el nuevo método
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "Examen físico de sueño guardado exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"Error al guardar el examen: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "Método no permitido.")
        return redirect("index")


@login_required
def guardar_sueno_anamnesis(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Crear o actualizar el resultado principal
            anamnesis, created = SuenoAnamnesisResult.objects.get_or_create(
                visita_examen=visita_examen
            )

            # ==============================
            # Guardar campos simples
            # ==============================
            campos_simples = [
                "motivo_consulta",
                "enfermedad_actual",
                "presenta_queja",
                "observaciones_queja",
                "causa_conocida",
                "especificacion_causa",
                "rutina_dormir",
                "describa_rutina",
                "jornada_laboral",
                "hora_acostarse_laboral",
                "tiempo_dormirse_laboral",
                "hora_intencion_dormir_laboral",
                "hora_despertar_laboral",
                "tiempo_salir_cama_laboral",
                "sueno_reparador_laboral",
                "companero_cama_laboral",
                "despertador_laboral",
                "jornada_fds",
                "hora_acostarse_fds",
                "tiempo_dormirse_fds",
                "hora_intencion_dormir_fds",
                "hora_despertar_fds",
                "tiempo_salir_cama_fds",
                "sueno_reparador_fds",
                "companero_cama_fds",
                "despertador_fds",
                "hora_acostarse_vacaciones",
                "tiempo_dormirse_vacaciones",
                "hora_intencion_dormir_vacaciones",
                "hora_despertar_vacaciones",
                "tiempo_salir_cama_vacaciones",
                "sueno_reparador_vacaciones",
                "companero_cama_vacaciones",
                "despertador_vacaciones",
                "realiza_siestas",
                "numero_siestas",
                "duracion_siestas",
                "siesta_frecuencia",
                "siesta_reparadora",
                "periodo_siestas",
                "iluminacion",
                "comodidad",
                "ruido",
                "consume",
                "consume_medicamento",
                "usa_pantallas",
                "cama_actividades",
                "actividad_fisica",
                "sintomas_sueno",
                "sintomas_diurnos",
                "observaciones",
            ]

            for campo in campos_simples:
                setattr(anamnesis, campo, request.POST.get(campo, ""))

            anamnesis.save()

            # ==============================
            # Guardar relaciones hijas
            # ==============================

            # Quejas de sueño
            anamnesis.tipos_queja_detalle.all().delete()
            nombres_quejas = request.POST.getlist("tipo_queja[]")
            for nombre in nombres_quejas:
                quejaId = nombre.replace(" ", "_").lower()
                TipoQuejaSueno.objects.create(
                    anamnesis=anamnesis,
                    nombre=nombre,
                    inicio=request.POST.get(f"{quejaId}_inicio", ""),
                    evolucion=request.POST.get(f"{quejaId}_evolucion", ""),
                    frecuencia=request.POST.get(f"{quejaId}_frecuencia", ""),
                    gravedad=request.POST.get(f"{quejaId}_gravedad", ""),
                )

            # Sustancias
            anamnesis.sustancias.all().delete()
            sustancias_tipos = request.POST.getlist("sustancias_tipo[]")
            sustancias_cantidades = request.POST.getlist("sustancias_cantidad[]")
            sustancias_frecuencias = request.POST.getlist("sustancias_frecuencia[]")
            sustancias_tiempos = request.POST.getlist("sustancias_tiempo[]")
            sustancias_observaciones = request.POST.getlist(
                "sustancias_observaciones[]"
            )

            for i, tipo in enumerate(sustancias_tipos):
                SustanciaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    cantidad=sustancias_cantidades[i]
                    if i < len(sustancias_cantidades)
                    else "",
                    frecuencia=sustancias_frecuencias[i]
                    if i < len(sustancias_frecuencias)
                    else "",
                    tiempo=sustancias_tiempos[i] if i < len(sustancias_tiempos) else "",
                    observaciones=sustancias_observaciones[i]
                    if i < len(sustancias_observaciones)
                    else "",
                )

            # Medicamentos
            anamnesis.medicamentos.all().delete()
            nombres = request.POST.getlist("nombre_medicamento[]")
            dosis = request.POST.getlist("dosis_medicamento[]")
            observaciones = request.POST.getlist("observaciones_medicamento[]")
            presentacion = request.POST.getlist("presentacion[]")
            veces_dia = request.POST.getlist("veces_dia[]")
            frecuencias = request.POST.getlist("frecuencia_medicamentos[]")
            tiempos = request.POST.getlist("tiempo_antes_dormir[]")

            for i, nombre in enumerate(nombres):
                MedicamentoSueno.objects.create(
                    anamnesis=anamnesis,
                    nombre=nombre,
                    dosis=dosis[i] if i < len(dosis) else "",
                    observaciones=observaciones[i] if i < len(observaciones) else "",
                    presentacion=presentacion[i] if i < len(presentacion) else "",
                    veces_dia=veces_dia[i] if i < len(veces_dia) else "",
                    frecuencia=frecuencias[i] if i < len(frecuencias) else "",
                    tiempo=tiempos[i] if i < len(tiempos) else "",
                )

            # Pantallas
            anamnesis.pantallas.all().delete()
            pantallas_tipos = request.POST.getlist("tipo_pantalla[]")
            pantallas_frecuencias = request.POST.getlist("pantalla_frecuencia[]")
            pantallas_tiempos = request.POST.getlist("pantalla_tiempo_dormir[]")

            for i, tipo in enumerate(pantallas_tipos):
                PantallaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    frecuencia=pantallas_frecuencias[i]
                    if i < len(pantallas_frecuencias)
                    else "",
                    tiempo_antes_dormir=pantallas_tiempos[i]
                    if i < len(pantallas_tiempos)
                    else "",
                )

            # Actividades en cama
            anamnesis.actividades_en_cama.all().delete()
            actividades_cama = request.POST.getlist("tipo_actividad[]")
            actividades_frec = request.POST.getlist("frecuencia_actividad[]")
            actividades_obs = request.POST.getlist("observaciones_actividades[]")

            for i, tipo in enumerate(actividades_cama):
                ActividadEnCamaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    frecuencia=actividades_frec[i] if i < len(actividades_frec) else "",
                    observaciones=actividades_obs[i]
                    if i < len(actividades_obs)
                    else "",
                )

            # Actividades físicas
            anamnesis.actividades_fisicas.all().delete()
            actfis_tipo = request.POST.getlist("tipo_actividad_fisica[]")
            actfis_otro = request.POST.getlist("tipo_actividad_otro_texto[]")
            actfis_intensidad = request.POST.getlist("intensidad_fisica[]")
            actfis_frec = request.POST.getlist("frecuencia_fisica[]")
            actfis_obs = request.POST.getlist("observaciones_actividad_fisica[]")

            for i, tipo in enumerate(actfis_tipo):
                ActividadFisicaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    otro_texto=actfis_otro[i] if i < len(actfis_otro) else "",
                    intensidad=actfis_intensidad[i]
                    if i < len(actfis_intensidad)
                    else "",
                    frecuencia=actfis_frec[i] if i < len(actfis_frec) else "",
                    observaciones=actfis_obs[i] if i < len(actfis_obs) else "",
                )

            # Síntomas de sueño
            anamnesis.sintomas_suenos.all().delete()
            sintomas_tipo = request.POST.getlist("tipo_sintoma[]")
            sintomas_inicio = request.POST.getlist("cuando_inicio[]")
            sintomas_evo = request.POST.getlist("evolucion[]")
            sintomas_frec = request.POST.getlist("frecuencia[]")
            sintomas_grav = request.POST.getlist("gravedad[]")
            sintomas_obs = request.POST.getlist("observaciones_sintoma[]")

            for i, tipo in enumerate(sintomas_tipo):
                SintomaSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    cuando_inicio=sintomas_inicio[i]
                    if i < len(sintomas_inicio)
                    else "",
                    evolucion=sintomas_evo[i] if i < len(sintomas_evo) else "",
                    frecuencia=sintomas_frec[i] if i < len(sintomas_frec) else "",
                    gravedad=sintomas_grav[i] if i < len(sintomas_grav) else "",
                    observaciones=sintomas_obs[i] if i < len(sintomas_obs) else "",
                )

            # Síntomas diurnos
            anamnesis.sintomas_diurno.all().delete()
            sintomasd_tipo = request.POST.getlist("tipo_sintoma_diurno[]")
            sintomasd_inicio = request.POST.getlist("cuando_inicio_diurno[]")
            sintomasd_evo = request.POST.getlist("evolucion_diurno[]")
            sintomasd_frec = request.POST.getlist("frecuencia_diurno[]")
            sintomasd_grav = request.POST.getlist("gravedad_diurno[]")
            sintomasd_obs = request.POST.getlist("observaciones_sintoma_diurno[]")

            for i, tipo in enumerate(sintomasd_tipo):
                SintomaDiurnoSueno.objects.create(
                    anamnesis=anamnesis,
                    tipo=tipo,
                    cuando_inicio=sintomasd_inicio[i]
                    if i < len(sintomasd_inicio)
                    else "",
                    evolucion=sintomasd_evo[i] if i < len(sintomasd_evo) else "",
                    frecuencia=sintomasd_frec[i] if i < len(sintomasd_frec) else "",
                    gravedad=sintomasd_grav[i] if i < len(sintomasd_grav) else "",
                    observaciones=sintomasd_obs[i] if i < len(sintomasd_obs) else "",
                )

            # ==============================
            # Marcar examen como completado
            # ==============================
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "Anamnesis de sueño guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"Error al guardar la anamnesis: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    messages.error(request, "Método no permitido.")
    return redirect("index")


@login_required
def guardar_atenas(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener respuestas de las preguntas (1-8)
            pregunta_1 = request.POST.get("induccion_dormir", "0")
            pregunta_2 = request.POST.get("despertares_noche", "0")
            pregunta_3 = request.POST.get("despertar_temprano", "0")
            pregunta_4 = request.POST.get("duracion_dormir", "0")
            pregunta_5 = request.POST.get("calidad_dormir", "0")
            pregunta_6 = request.POST.get("bienestar_dia", "0")
            pregunta_7 = request.POST.get("funcionamiento_dia", "0")
            pregunta_8 = request.POST.get("somnolencia_dia", "0")

            # Calcular puntuación total
            puntuacion_total = request.POST.get("puntuacion_total", "0")

            # Crear o actualizar el resultado de Atenas
            atenas, created = AtenasResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Preguntas individuales
                    "induccion_dormir": pregunta_1,
                    "despertares_noche": pregunta_2,
                    "despertar_temprano": pregunta_3,
                    "duracion_dormir": pregunta_4,
                    "calidad_dormir": pregunta_5,
                    "bienestar_dia": pregunta_6,
                    "funcionamiento_dia": pregunta_7,
                    "somnolencia_dia": pregunta_8,
                    # Puntuación y interpretación
                    "puntuacion_total": puntuacion_total,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Escala de Atenas guardada exitosamente. Puntuación: {puntuacion_total}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la escala de Atenas: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_berlin(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener los campos según tu modelo BerlinResult
            peso_cambio = request.POST.get("peso_cambio", "")
            ronca = request.POST.get("ronca", "")
            tipo_ronquido = request.POST.get("tipo_ronquido", "")
            frecuencia_ronquidos = request.POST.get("frecuencia_ronquidos", "")
            ronquido_molesto = request.POST.get("ronquido_molesto", "")
            apnea_observada = request.POST.get("apnea_observada", "")
            fatiga_matutina = request.POST.get("fatiga_matutina", "")
            fatiga_dia = request.POST.get("fatiga_dia", "")
            somnolencia_conducir = request.POST.get("somnolencia_conducir", "")
            presion_alta = request.POST.get("presion_alta", "")

            # Crear o actualizar el resultado de Berlín usando los campos exactos del modelo
            berlin, created = BerlinResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos exactos según tu modelo BerlinResult
                    "peso_cambio": peso_cambio,
                    "ronca": ronca,
                    "tipo_ronquido": tipo_ronquido,
                    "frecuencia_ronquidos": frecuencia_ronquidos,
                    "ronquido_molesto": ronquido_molesto,
                    "apnea_observada": apnea_observada,
                    "fatiga_matutina": fatiga_matutina,
                    "fatiga_dia": fatiga_dia,
                    "somnolencia_conducir": somnolencia_conducir,
                    "presion_alta": presion_alta,
                },
            )
            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Cuestionario de Berlín guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el cuestionario de Berlín: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Epworth(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener las respuestas según los nombres en tu HTML
            sentado_leyendo = request.POST.get("epworth_leyendo", "0")
            viendo_tv = request.POST.get("epworth_tv", "0")
            sentado_teatro = request.POST.get("epworth_teatro", "0")
            pasajero_coche = request.POST.get("epworth_pasajero", "0")
            tumbado_tarde = request.POST.get("epworth_tumbado", "0")
            charlando = request.POST.get("epworth_charlando", "0")
            despues_comer = request.POST.get("epworth_comida", "0")
            trafico = request.POST.get("epworth_trafico", "0")

            # Calcular puntuación total
            puntaje_total = (
                sentado_leyendo
                + viendo_tv
                + sentado_teatro
                + pasajero_coche
                + tumbado_tarde
                + charlando
                + despues_comer
                + trafico
            )

            # Crear o actualizar el resultado de Epworth usando los campos exactos del modelo
            epworth, created = EpworthResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos exactos según tu modelo EpworthResult
                    "sentado_leyendo": sentado_leyendo,
                    "viendo_tv": viendo_tv,
                    "sentado_teatro": sentado_teatro,
                    "pasajero_coche": pasajero_coche,
                    "tumbado_tarde": tumbado_tarde,
                    "charlando": charlando,
                    "despues_comer": despues_comer,
                    "trafico": trafico,
                    "puntaje_total": puntaje_total,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, f"✅ Escala de Epworth guardada exitosamente.\n")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la escala de Epworth: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_ISI(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener las respuestas del formulario
            dificultad_dormir = request.POST.get("dificultad_dormir", "")
            dificultad_mantener_sueno = request.POST.get(
                "dificultad_mantener_sueno", ""
            )
            despertar_temprano = request.POST.get("despertar_temprano", "")
            satisfaccion_sueno = request.POST.get("satisfaccion_sueno", "")
            notabilidad_problema = request.POST.get("notabilidad_problema", "")
            preocupacion_sueno = request.POST.get("preocupacion_sueno", "")
            interferencia_sueno = request.POST.get("interferencia_sueno", "")

            puntuacion = request.POST.get("puntuacion_total", "0")

            # Crear o actualizar el resultado ISI
            isi_result, created = ISIResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "dificultad_dormir": dificultad_dormir,
                    "dificultad_mantener_sueno": dificultad_mantener_sueno,
                    "despertar_temprano": despertar_temprano,
                    "satisfaccion_sueno": satisfaccion_sueno,
                    "notabilidad_problema": notabilidad_problema,
                    "preocupacion_sueno": preocupacion_sueno,
                    "interferencia_sueno": interferencia_sueno,
                    "puntuacion_total": puntuacion,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Índice de Severidad del Insomnio (ISI) guardado exitosamente.\n",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar el ISI: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_MEW(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener los campos según tu modelo MEWResult
            hora_levantarse = request.POST.get("hora_levantarse_meq", "")
            hora_acostarse = request.POST.get("hora_acostarse_meq", "")
            uso_despertador = request.POST.get("uso_despertador_meq", "")
            facilidad_levantarse = request.POST.get("facilidad_levantarse_meq", "")
            alerta_manana = request.POST.get("alerta_manana_meq", "")
            apetito_manana = request.POST.get("apetito_manana_meq", "")
            descanso_manana = request.POST.get("descanso_manana_meq", "")
            hora_acostarse_libre = request.POST.get("hora_acostarse_libre_meq", "")
            ejercicio_fisico = request.POST.get("ejercicio_fisico_meq", "")
            hora_cansancio_noche = request.POST.get("hora_cansancio_noche_meq", "")
            nivel_cansancia_11 = request.POST.get("nivel_cansancia_11", "")
            hora_despertarse_si_tarde = request.POST.get(
                "hora_despertarse_si_tarde", ""
            )
            guardia_nocturna = request.POST.get("guardia_nocturna", "")
            horario_trabajo_fisico = request.POST.get("horario_trabajo_fisico", "")
            ejercicio_nocturno = request.POST.get("ejercicio_nocturno", "")
            horario_trabajo = request.POST.get("horario_trabajo", "")
            maximo_bienestar = request.POST.get("maximo_bienestar", "")
            tipo_persona = request.POST.get("tipo_persona", "")

            # Función para calcular la puntuación MEW
            def calcular_puntuacion_mew(respuestas_dict):
                """Calcula la puntuación del cuestionario MEW (Morningness-Eveningness)"""
                puntuacion = 0

                # Pregunta 1: Hora de levantarse (5-25, 4-30, 3-45, 2-60)
                hora_lev = respuestas_dict.get("hora_levantarse", "")
                if "5:00-6:30" in hora_lev or "5:00" in hora_lev or "6:30" in hora_lev:
                    puntuacion += 5
                elif "6:30-7:45" in hora_lev or "7:45" in hora_lev:
                    puntuacion += 4
                elif "7:45-9:45" in hora_lev or "9:45" in hora_lev:
                    puntuacion += 3
                elif "9:45-11:00" in hora_lev or "11:00" in hora_lev:
                    puntuacion += 2
                elif "11:00" in hora_lev:
                    puntuacion += 1

                # Pregunta 2: Hora de acostarse
                hora_acos = respuestas_dict.get("hora_acostarse", "")
                if "8:00-9:00" in hora_acos:
                    puntuacion += 5
                elif "9:00-10:15" in hora_acos:
                    puntuacion += 4
                elif "10:15-12:30" in hora_acos:
                    puntuacion += 3
                elif "12:30-1:45" in hora_acos:
                    puntuacion += 2
                elif "1:45-3:00" in hora_acos:
                    puntuacion += 1

                # Pregunta 3: Uso de despertador
                despertador = respuestas_dict.get("uso_despertador", "")
                if "Completamente" in despertador or "completamente" in despertador:
                    puntuacion += 4
                elif "Moderadamente" in despertador or "moderadamente" in despertador:
                    puntuacion += 3
                elif "Ligeramente" in despertador or "ligeramente" in despertador:
                    puntuacion += 2
                elif "Para nada" in despertador or "nada" in despertador:
                    puntuacion += 1

                # Continuar con el resto de preguntas...
                # (Simplificado para el ejemplo)

                return puntuacion

            # Calcular puntuación
            respuestas = {
                "hora_levantarse": hora_levantarse,
                "hora_acostarse": hora_acostarse,
                "uso_despertador": uso_despertador,
                "facilidad_levantarse": facilidad_levantarse,
                "alerta_manana": alerta_manana,
                "apetito_manana": apetito_manana,
                "descanso_manana": descanso_manana,
                "hora_acostarse_libre": hora_acostarse_libre,
                "ejercicio_fisico": ejercicio_fisico,
                "hora_cansancio_noche": hora_cansancio_noche,
                "nivel_cansancia_11": nivel_cansancia_11,
                "hora_despertarse_si_tarde": hora_despertarse_si_tarde,
                "guardia_nocturna": guardia_nocturna,
                "horario_trabajo_fisico": horario_trabajo_fisico,
                "ejercicio_nocturno": ejercicio_nocturno,
                "horario_trabajo": horario_trabajo,
                "maximo_bienestar": maximo_bienestar,
                "tipo_persona": tipo_persona,
            }

            puntuacion_calculada = calcular_puntuacion_mew(respuestas)
            puntuacion_form = request.POST.get("puntuacion", str(puntuacion_calculada))

            try:
                puntuacion_final = (
                    int(puntuacion_form)
                    if puntuacion_form.isdigit()
                    else puntuacion_calculada
                )
            except:
                puntuacion_final = puntuacion_calculada

            # Determinar cronotipo según puntuación MEW
            if puntuacion_final >= 70:
                tipo_persona_calculado = "Definitivamente matutino"
            elif puntuacion_final >= 59:
                tipo_persona_calculado = "Moderadamente matutino"
            elif puntuacion_final >= 42:
                tipo_persona_calculado = "Ni matutino ni vespertino"
            elif puntuacion_final >= 31:
                tipo_persona_calculado = "Moderadamente vespertino"
            else:
                tipo_persona_calculado = "Definitivamente vespertino"

            # Crear o actualizar el resultado MEW usando los campos exactos del modelo
            mew_result, created = MEWResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos exactos según tu modelo MEWResult
                    "hora_levantarse": hora_levantarse,
                    "hora_acostarse": hora_acostarse,
                    "uso_despertador": uso_despertador,
                    "facilidad_levantarse": facilidad_levantarse,
                    "alerta_manana": alerta_manana,
                    "apetito_manana": apetito_manana,
                    "descanso_manana": descanso_manana,
                    "hora_acostarse_libre": hora_acostarse_libre,
                    "ejercicio_fisico": ejercicio_fisico,
                    "hora_cansancio_noche": hora_cansancio_noche,
                    "nivel_cansancia_11": nivel_cansancia_11,
                    "hora_despertarse_si_tarde": hora_despertarse_si_tarde,
                    "guardia_nocturna": guardia_nocturna,
                    "horario_trabajo_fisico": horario_trabajo_fisico,
                    "ejercicio_nocturno": ejercicio_nocturno,
                    "horario_trabajo": horario_trabajo,
                    "maximo_bienestar": maximo_bienestar,
                    "tipo_persona": tipo_persona or tipo_persona_calculado,
                    "puntuacion": puntuacion_final,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Cuestionario MEW guardado exitosamente.\n"
                f"📊 Puntuación: {puntuacion_final}/86 - {tipo_persona_calculado}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el cuestionario MEW: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Pitsburg(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener los campos según los NOMBRES EXACTOS del modelo PittsburghResult
            hora_acostarse = request.POST.get("hora_acostarse", "")
            hora_levantarse = request.POST.get("hora_levantarse", "")
            latencia_sueno = request.POST.get("latencia_sueno", "0")
            horas_dormidas = request.POST.get(
                "horas_sueno_real", "0"
            )  # ✅ CAMPO CORRECTO DEL MODELO

            # Problemas durante el sueño - NOMBRES EXACTOS DEL MODELO
            conciliar_sueno = request.POST.get("conciliar_sueno", "")
            despertarse_sueno = request.POST.get("despertarse_sueno", "")
            levantarse_servicio_sueno = request.POST.get(
                "levantarse_servicio_sueno", ""
            )
            respirar = request.POST.get("respirar", "")
            toser_roncar_sueno = request.POST.get("toser_roncar_sueno", "")
            sentir_frio_sueno = request.POST.get(
                "sentir_frio_sueno", ""
            )  # ✅ Sin mayúscula
            calor_sueno = request.POST.get("calor_sueno", "")
            pesadillas_sueno = request.POST.get("pesadillas_sueno", "")
            dolores_sueno = request.POST.get("dolores_sueno", "")
            otras_razones = request.POST.get(
                "otras_razones", ""
            )  # ✅ NOMBRE CORRECTO DEL MODELO
            otras_sueno = request.POST.get("otras_sueno", "")

            # Evaluación general - NOMBRES EXACTOS DEL MODELO
            calidad_sueno = request.POST.get("calidad_sueno", "")
            medicinas_sueno = request.POST.get("medicinas_sueno", "")
            somnolencia_sueno = request.POST.get("somnolencia_sueno", "")
            problemas_animos_sueno = request.POST.get("problemas_animos_sueno", "")

            # Información de compañía - NOMBRES EXACTOS DEL MODELO
            duerme_acompanado = request.POST.get("duerme_acompanado", "")
            ronquidos_ruidosos = request.POST.get("ronquidos_ruidosos", "")
            pausas_respiracion = request.POST.get("pausas_respiracion", "")
            sacudidas_piernas = request.POST.get("sacudidas_piernas", "")
            desorientacion_confusion = request.POST.get("desorientacion_confusion", "")
            descripcion_inconvenientes = request.POST.get(
                "descripcion_inconvenientes", ""
            )
            otros_inconvenientes = request.POST.get("otros_inconvenientes", "")
            # Convertir valores numéricos
            try:
                latencia_sueno_num = float(latencia_sueno) if latencia_sueno else 0
                horas_sueno_real_num = (
                    float(horas_dormidas) if horas_dormidas else 0
                )  # ✅ VARIABLE CORRECTA
            except ValueError:
                latencia_sueno_num = 0
                horas_sueno_real_num = 0

            # Crear o actualizar el resultado Pittsburgh usando los CAMPOS EXACTOS del modelo
            pitsburg_result, created = PittsburghResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos de tiempo - NOMBRES EXACTOS DEL MODELO
                    "hora_acostarse": hora_acostarse,
                    "hora_levantarse": hora_levantarse,
                    "latencia_sueno": latencia_sueno_num,
                    "horas_dormidas": horas_sueno_real_num,  # ✅ CAMPO CORRECTO DEL MODELO
                    # Problemas durante el sueño - NOMBRES EXACTOS DEL MODELO
                    "conciliar_sueno": conciliar_sueno,
                    "despertarse_sueno": despertarse_sueno,
                    "levantarse_servicio_sueno": levantarse_servicio_sueno,
                    "respirar": respirar,
                    "toser_roncar_sueno": toser_roncar_sueno,
                    "sentir_frio_sueno": sentir_frio_sueno,
                    "calor_sueno": calor_sueno,
                    "pesadillas_sueno": pesadillas_sueno,
                    "dolores_sueno": dolores_sueno,
                    "otras_razones": otras_razones,  # ✅ CAMPO CORRECTO DEL MODELO
                    "otras_sueno": otras_sueno,
                    # Evaluación general - NOMBRES EXACTOS DEL MODELO
                    "calidad_sueno": calidad_sueno,
                    "medicinas_sueno": medicinas_sueno,
                    "somnolencia_sueno": somnolencia_sueno,
                    "problemas_animos_sueno": problemas_animos_sueno,
                    # Información de compañía - NOMBRES EXACTOS DEL MODELO
                    "duerme_acompanado": duerme_acompanado,
                    "ronquidos_ruidosos": ronquidos_ruidosos,
                    "pausas_respiracion": pausas_respiracion,
                    "sacudidas_piernas": sacudidas_piernas,
                    "desorientacion_confusion": desorientacion_confusion,
                    "descripcion_inconvenientes": descripcion_inconvenientes,
                    "otros_inconvenientes": otros_inconvenientes,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Cuestionario de Pittsburgh guardado exitosamente.\n"
                f"📊 Hora acostarse: {hora_acostarse} | Hora levantarse: {hora_levantarse}\n"
                f"🛏️ Calidad de sueño: {calidad_sueno}\n"
                f"⏰ Horas de sueño: {horas_sueno_real_num}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el cuestionario de Pittsburgh: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_StopBang(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # CAMBIO: Convertir valores correctamente (ahora recibimos "0" y "1")
            def convert_to_bool(value):
                """Convierte valor del formulario a booleano"""
                if value is None:
                    return False
                # Si viene como string "1" o "0"
                if isinstance(value, str):
                    return value == "1" or value.lower() == "true"
                # Si viene como entero
                return bool(int(value)) if str(value).isdigit() else False

            # Aplicar conversión a todos los campos
            ronca_fuerte = convert_to_bool(request.POST.get("ronca_fuerte"))
            cansado_frecuencia = convert_to_bool(request.POST.get("cansado_frecuencia"))
            deja_respirar = convert_to_bool(request.POST.get("deja_respirar"))
            presion_arterial = convert_to_bool(request.POST.get("presion_arterial"))
            imc_alto = convert_to_bool(request.POST.get("imc_alto"))
            mayor_50 = convert_to_bool(request.POST.get("mayor_50"))
            cuello_grande = convert_to_bool(request.POST.get("cuello_grande"))
            masculino = convert_to_bool(request.POST.get("masculino"))

            # Calcular puntuación
            campos = [
                ronca_fuerte,
                cansado_frecuencia,
                deja_respirar,
                presion_arterial,
                imc_alto,
                mayor_50,
                cuello_grande,
                masculino,
            ]
            puntaje_total = sum(campos)

            # STOP (primeros 4) y BANG (últimos 4)
            stop_positivos = sum(campos[:4])
            bang_positivos = sum(campos[4:])

            # Determinar riesgo
            if puntaje_total <= 2:
                riesgo = "Bajo"
            elif puntaje_total <= 4:
                riesgo = "Intermedio"
            else:
                riesgo = "Alto"

            # Alternativa: alto riesgo si STOP≥2 y BANG≥2
            alto_riesgo_alternativo = stop_positivos >= 2 and bang_positivos >= 2

            # Guardar resultado en la BD
            stopbang_result, created = StopBangResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "ronca_fuerte": ronca_fuerte,
                    "cansado_frecuencia": cansado_frecuencia,
                    "deja_respirar": deja_respirar,
                    "presion_arterial": presion_arterial,
                    "imc_alto": imc_alto,
                    "mayor_50": mayor_50,
                    "cuello_grande": cuello_grande,
                    "masculino": masculino,
                    "puntaje_total": puntaje_total,
                    "riesgo": riesgo,
                    "stop_positivos": stop_positivos,
                    "bang_positivos": bang_positivos,
                    "alto_riesgo_alternativo": alto_riesgo_alternativo,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Cuestionario STOP-BANG guardado exitosamente.\n"
                f"📊 Puntuación: {puntaje_total}/8 - {riesgo} riesgo\n"
                f"🔍 STOP: {stop_positivos} | BANG: {bang_positivos}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el cuestionario STOP-BANG: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


### Anosognosia


@login_required
def guardar_examen_Participante_EuroQoL(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener las respuestas del formulario
            movilidad = request.POST.get("movilidad")
            cuidado_personal = request.POST.get("cuidado_personal")
            actividades = request.POST.get("actividades")
            dolor = request.POST.get("dolor")
            ansiedad = request.POST.get("ansiedad")

            # Crear o actualizar el resultado del EuroQol
            euroqol, created = EuroQol5D5LResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "movilidad": movilidad,
                    "cuidado_personal": cuidado_personal,
                    "actividades": actividades,
                    "dolor": dolor,
                    "ansiedad": ansiedad,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Cuestionario EuroQol-5D-5L guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el cuestionario EuroQol-5D-5L: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_LawtonBrody(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Buscar la visita-examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Si está pendiente, lo pasamos a en progreso
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Extraer respuestas
            genero = request.POST.get("genero")

            usar_telefono = request.POST.get("usar_telefono_text")
            hacer_compras = request.POST.get("hacer_compras_text")
            preparar_comida = request.POST.get("preparar_comida_text")
            cuidado_casa = request.POST.get("cuidado_casa_text")
            lavar_ropa = request.POST.get("lavar_ropa_text")
            uso_transporte = request.POST.get("uso_transporte_text")
            medicacion = request.POST.get("medicacion_text")
            manejo_dinero = request.POST.get("manejo_dinero_text")

            puntaje_total = request.POST.get("total")
            diagnostico = request.POST.get("diagnostico")

            # Guardar o actualizar resultado
            lawtonbrody, created = LawtonBrodyResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "genero": genero,
                    "usar_telefono": usar_telefono,
                    "hacer_compras": hacer_compras,
                    "preparar_comida": preparar_comida,
                    "cuidado_casa": cuidado_casa,
                    "lavar_ropa": lavar_ropa,
                    "uso_transporte": uso_transporte,
                    "medicacion": medicacion,
                    "manejo_dinero": manejo_dinero,
                    "puntaje_total": puntaje_total,
                    "diagnostico": diagnostico,
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Escala de Lawton y Brody guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el examen Lawton y Brody: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_Yesavage(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Extraer respuestas
            campos = [
                "satisfaccion_vida",
                "disminuir_actividades",
                "vida_vacia",
                "aburrido_frecuente",
                "buen_animo",
                "preocupacion",
                "felicidad",
                "frecuencia_desamparado",
                "quedarse_casa",
                "problemas_memoria",
                "maravilla_vivir",
                "inutil",
                "lleno_energia",
                "sin_esperanza",
                "otras_personas_mejor",
            ]
            respuestas = {campo: request.POST.get(campo) for campo in campos}

            puntaje_total = request.POST.get("puntaje_total")
            interpretacion = request.POST.get("interpretacion")

            # Guardar en la BD
            yesavage, created = ParticipanteYesavageResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    **respuestas,
                    "puntaje_total": puntaje_total,
                    "interpretacion": interpretacion,
                },
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                "✅ Escala de Depresión Geriátrica de Yesavage guardada exitosamente.",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hay error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el examen de Yesavage: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_EVA_EuroQoL(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener el valor del termómetro
            termometro_estado_salud = request.POST.get("termometro_estado_salud")

            # Crear o actualizar el resultado
            evaeuroqol, created = EuroQolEVASaludResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "termometro_estado_salud": termometro_estado_salud,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                "✅ Autovaloración del Estado de Salud (EVA EuroQol) guardada exitosamente.",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar la Autovaloración del Estado de Salud (EVA EuroQol): {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_NPI(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Lista de ítems del NPI
            items = [
                "ideas_delirantes",
                "alucinaciones",
                "agitacion",
                "depresion",
                "ansiedad",
                "euforia",
                "apatia",
                "desinhibicion",
                "irritabilidad",
                "conducta_motor",
                "sueno",
                "apetito",
            ]

            data = {}
            for item in items:
                data[item] = request.POST.get(item)

                # frec = request.POST.get(f"{item}_frecuencia") or request.POST.get(f"{item}_frecuencia_texto")
                # grav = request.POST.get(f"{item}_gravedad") or request.POST.get(f"{item}_gravedad_texto")
                # dist = request.POST.get(f"{item}_distres") or request.POST.get(f"{item}_distres_texto")
                # fg = request.POST.get(f"{item}_resultado") or 0

                # data[f"{item}_frecuencia"] = frec
                # data[f"{item}_gravedad"] = grav
                # data[f"{item}_F_G"] = fg
                # data[f"{item}_distres"] = dist
                data[f"{item}_frecuencia"] = request.POST.get(
                    f"{item}_frecuencia_texto"
                )
                data[f"{item}_gravedad"] = request.POST.get(f"{item}_gravedad_texto")
                data[f"{item}_F_G"] = request.POST.get(f"{item}_resultado")
                data[f"{item}_distres"] = request.POST.get(f"{item}_distres_texto")

                data["carga_total"] = request.POST.get("carga_total", 0)

            # Crear o actualizar el resultado del NPI
            npi, created = CuidadorNPIResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=data
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Inventario Neuropsiquiátrico (NPI) guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar el Inventario Neuropsiquiátrico (NPI): {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_AQD(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Buscar la visita asociada
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Cambiar estado si estaba pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos de la escala (30 ítems)
            campos = [
                "recordar_fecha",
                "orientacion_lugares_nuevos",
                "recordar_llamadas",
                "entender_conversacion",
                "firmar",
                "entender_lectura",
                "mantener_orden",
                "recordar_lugar_objetos",
                "escribir",
                "manejar_dinero",
                "orientacion_zona_donde_vive",
                "recordar_citas",
                "pasatiempos",
                "comunicarse_con_gente",
                "calculos_mentales",
                "recordar_compras",
                "contener_orina",
                "entender_pelicula",
                "orientacion_en_casa",
                "hacer_tareas_hogar",
                "comer_solo",
                "realizar_tramites",
                "decisiones_y_adaptacion",
                "egoismo",
                "enojo_menos_paciencia",
                "llorar_con_facilidad",
                "reir_situaciones_inapropiadas",
                "temas_sexuales",
                "falta_de_interes",
                "deprimido",
            ]

            # Extraer respuestas
            respuestas = {campo: request.POST.get(campo + "_texto") for campo in campos}

            # Calcular puntaje total (30 a 120)
            puntaje_total = 0
            for campo in campos:
                try:
                    valor = int(request.POST.get(campo, 0))
                    puntaje_total += valor
                except ValueError:
                    pass

            # Guardar o actualizar registro
            aqdcuidador, created = AQDCuidadorResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    **respuestas,
                    # "puntaje_total": puntaje_total,  # si luego agregas este campo al modelo
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Escala AQ-D Cuidador guardada correctamente. Puntaje total: {puntaje_total}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la escala AQ-D Cuidador: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_AQD(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Buscar la visita asociada
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos (30 ítems)
            campos = [
                "recordar_fecha",
                "orientacion_lugares_nuevos",
                "recordar_llamadas",
                "entender_conversacion",
                "firmar",
                "entender_lectura",
                "mantener_orden",
                "recordar_lugar_objetos",
                "escribir",
                "manejar_dinero",
                "orientacion_zona_donde_vive",
                "recordar_citas",
                "pasatiempos",
                "comunicarse_con_gente",
                "calculos_mentales",
                "recordar_compras",
                "contener_orina",
                "entender_pelicula",
                "orientacion_en_casa",
                "hacer_tareas_hogar",
                "comer_solo",
                "realizar_tramites",
                "decisiones_y_adaptacion",
                "egoismo",
                "enojo_menos_paciencia",
                "llorar_con_facilidad",
                "reir_situaciones_inapropiadas",
                "temas_sexuales",
                "falta_de_interes",
                "deprimido",
            ]

            # Extraer respuestas
            respuestas = {campo: request.POST.get(campo + "_texto") for campo in campos}

            # Calcular puntaje total
            puntaje_total = 0
            for campo in campos:
                try:
                    valor = int(request.POST.get(campo, 0))
                    puntaje_total += valor
                except ValueError:
                    pass

            # Guardar en BD (update si ya existe)
            aqdparticipante, created = AQDParticipanteResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    **respuestas,
                    # Si luego necesitas un campo en el modelo, lo puedes añadir
                    # "puntaje_total": puntaje_total,
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Escala AQ-D Participante guardada exitosamente. Puntaje total: {puntaje_total}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si falla
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la escala AQ-D Participante: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_CDR(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Construimos diccionario con TODAS las respuestas
            defaults = {}

            # Iteramos sobre los campos definidos en el modelo
            for field in CDRParticipanteResult._meta.get_fields():
                if field.name in ["id", "visita_examen", "resultadoexamenbase_ptr"]:
                    continue  # ignorar claves y herencia
                if (
                    hasattr(field, "get_internal_type")
                    and field.get_internal_type() == "BooleanField"
                ):
                    defaults[field.name] = bool(request.POST.get(field.name))
                else:
                    value = request.POST.get(field.name)
                    defaults[field.name] = value if value != "" else None

            # Crear o actualizar el resultado
            cdrparticipante, created = CDRParticipanteResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults=defaults,
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Cuestionario CDR - Participante guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar el cuestionario CDR - Participante: {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Participante_MoCA(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener los campos EXACTOS del modelo MoCAResult
            alternancia = int(request.POST.get("alternancia", 0))
            cubo = int(request.POST.get("cubo", 0))
            reloj = int(request.POST.get("reloj", 0))
            denominacion = int(request.POST.get("denominacion", 0))
            atencion = int(request.POST.get("atencion", 0))
            repeticion = int(request.POST.get("repeticion", 0))
            fluidez = int(request.POST.get("fluidez", 0))
            abstraccion = int(request.POST.get("abstraccion", 0))
            diferido = int(request.POST.get("diferido", 0))
            orientacion = int(request.POST.get("orientacion", 0))
            educacion_baja = (
                True if request.POST.get("educacion_baja") == "on" else False
            )

            # Calcular puntaje total
            puntaje_total = (
                alternancia
                + cubo
                + reloj
                + denominacion
                + atencion
                + repeticion
                + fluidez
                + abstraccion
                + diferido
                + orientacion
            )

            if educacion_baja and puntaje_total < 30:
                puntaje_total += 1

            # Determinar interpretación
            if puntaje_total >= 26:
                interpretacion = "Puntaje normal (función cognitiva preservada)"
            else:
                interpretacion = "Posible deterioro cognitivo. Se recomienda evaluación clínica adicional."

            # Crear o actualizar el resultado
            moca, created = MoCAResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "alternancia": alternancia,
                    "cubo": cubo,
                    "reloj": reloj,
                    "denominacion": denominacion,
                    "atencion": atencion,
                    "repeticion": repeticion,
                    "fluidez": fluidez,
                    "abstraccion": abstraccion,
                    "diferido": diferido,
                    "orientacion": orientacion,
                    "educacion_baja": educacion_baja,
                    "puntaje_total": puntaje_total,
                    "interpretacion": interpretacion,
                },
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Escala MoCA guardada exitosamente.\n"
                f"📊 Puntaje: {puntaje_total}/30\n"
                f"🔍 Interpretación: {interpretacion}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar la escala MoCA: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_CDR(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Recoger todos los campos EXACTOS del modelo
            campos = {
                "memoria_p1": request.POST.get("memoria_p1", ""),
                "memoria_p1_1": request.POST.get("memoria_p1_1", ""),
                "memoria_p2": request.POST.get("memoria_p2", ""),
                "memoria_p3": request.POST.get("memoria_p3", ""),
                "memoria_p4": request.POST.get("memoria_p4", ""),
                "memoria_p5": request.POST.get("memoria_p5", ""),
                "memoria_p6": request.POST.get("memoria_p6", ""),
                "memoria_p7": request.POST.get("memoria_p7", ""),
                "memoria_p8": request.POST.get("memoria_p8", ""),
                "evento_recuerda_semana": request.POST.get(
                    "evento_recuerda_semana", ""
                ),
                "evento_recuerda_mes": request.POST.get("evento_recuerda_mes", ""),
                "nacimiento_fecha": request.POST.get("nacimiento_fecha") or None,
                "nacimiento_lugar": request.POST.get("nacimiento_lugar", ""),
                "colegio_nombre": request.POST.get("colegio_nombre", ""),
                "colegio_lugar": request.POST.get("colegio_lugar", ""),
                "colegio_grado": request.POST.get("colegio_grado", ""),
                "ocupacion_principal": request.POST.get("ocupacion_principal", ""),
                "ultimo_trabajo": request.POST.get("ultimo_trabajo", ""),
                "jubilacion": request.POST.get("jubilacion", ""),
                "orientacion_p1": request.POST.get("orientacion_p1", ""),
                "orientacion_p2": request.POST.get("orientacion_p2", ""),
                "orientacion_p3": request.POST.get("orientacion_p3", ""),
                "orientacion_p4": request.POST.get("orientacion_p4", ""),
                "orientacion_p5": request.POST.get("orientacion_p5", ""),
                "orientacion_p6": request.POST.get("orientacion_p6", ""),
                "orientacion_p7": request.POST.get("orientacion_p7", ""),
                "orientacion_p8": request.POST.get("orientacion_p8", ""),
                "juicio_p1": request.POST.get("juicio_p1", ""),
                "juicio_p2": request.POST.get("juicio_p2", ""),
                "juicio_p3": request.POST.get("juicio_p3", ""),
                "juicio_p4": request.POST.get("juicio_p4", ""),
                "juicio_p5": request.POST.get("juicio_p5", ""),
                "juicio_p6": request.POST.get("juicio_p6", ""),
                "trabaja_actualmente": request.POST.get("trabaja_actualmente", ""),
                "memoria_causa_jubilacion": request.POST.get(
                    "memoria_causa_jubilacion", ""
                ),
                "dificultades_trabajo_memoria": request.POST.get(
                    "dificultades_trabajo_memoria", ""
                ),
                "condujo_alguna_vez": request.POST.get("condujo_alguna_vez", ""),
                "conduce_actualmente": request.POST.get("conduce_actualmente", ""),
                "dejo_de_conducir_por_memoria": request.POST.get(
                    "dejo_de_conducir_por_memoria", ""
                ),
                "riesgos_conduccion": request.POST.get("riesgos_conduccion", ""),
                "compras_independientes": request.POST.get(
                    "compras_independientes", ""
                ),
                "actividades_fuera_hogar": request.POST.get(
                    "actividades_fuera_hogar", ""
                ),
                "asiste_funciones_sociales": request.POST.get(
                    "asiste_funciones_sociales", ""
                ),
                "motivo_no_funciones": request.POST.get("motivo_no_funciones", ""),
                "parece_enfermo": request.POST.get("parece_enfermo", ""),
                "participa_hogar_geriatrico": request.POST.get(
                    "participa_hogar_geriatrico", ""
                ),
                "info_suficiente_comunitarias": request.POST.get(
                    "info_suficiente_comunitarias", ""
                ),
                "notas_comunitarias": request.POST.get("notas_comunitarias", ""),
                "cambios_tareas_domesticas": request.POST.get(
                    "cambios_tareas_domesticas", ""
                ),
                "cosas_que_aun_realiza_domesticas": request.POST.get(
                    "cosas_que_aun_realiza_domesticas", ""
                ),
                "cambios_pasatiempos": request.POST.get("cambios_pasatiempos", ""),
                "cosas_que_aun_realiza_pasatiempos": request.POST.get(
                    "cosas_que_aun_realiza_pasatiempos", ""
                ),
                "actividades_no_realiza_en_hogar": request.POST.get(
                    "actividades_no_realiza_en_hogar", ""
                ),
                "habilidad_domestica_dementia_scale": request.POST.get(
                    "habilidad_domestica_dementia_scale"
                )
                or None,
                "descripcion_habilidad_domestica": request.POST.get(
                    "descripcion_habilidad_domestica", ""
                ),
                "nivel_desempeno_domestico": request.POST.get(
                    "nivel_desempeno_domestico", ""
                ),
                "notas_domesticas_pasatiempos": request.POST.get(
                    "notas_domesticas_pasatiempos", ""
                ),
                "cuidado_p1": request.POST.get("cuidado_p1") or None,
                "cuidado_p2": request.POST.get("cuidado_p2") or None,
                "cuidado_p3": request.POST.get("cuidado_p3") or None,
                "cuidado_p4": request.POST.get("cuidado_p4") or None,
            }

            # Guardar o actualizar
            cdrcuidador, created = CDRCuidadorResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=campos
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "✅ Escala CDR (Cuidador) guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request, f"❌ Error al guardar el cuestionario CDR (Cuidador): {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_RedLatSpanish(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de la visita
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Si está pendiente, marcar como en progreso
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Recoger los campos EXACTOS del modelo
            campos = {
                k: request.POST.get(k + "_texto", "")
                for k in [
                    # Autocuidado
                    "comer",
                    "vestirse",
                    "banarse",
                    "bano",
                    "medicamentos",
                    "apariencia",
                    # Cuidado del hogar
                    "cocinar",
                    "poner_mesa",
                    "aseo_hogar",
                    "mantener_casa",
                    "reparar_hogar",
                    "lavado_ropa",
                    # Trabajo y recreación
                    "trabajo",
                    "recreacion",
                    "organizaciones",
                    "desplazamiento",
                    # Compras y dinero
                    "alimentos",
                    "dinero_efectivo",
                    "finanzas",
                    # Viajes
                    "transporte_publico",
                    "manejo_vehiculos",
                    "movilidad_barrio",
                    "viajes_fuera",
                    # Comunicación
                    "telefono",
                    "conversacion",
                    "comprension",
                    "lectura",
                    "escritura",
                    # Tecnología
                    "computador",
                    "telefono_celular",
                    "cajero",
                    "internet",
                    "email",
                    "redes_sociales",
                ]
            }

            # Recoger los puntajes de cada sección
            puntajes = {
                "puntaje_autocuidado": request.POST.get("puntaje_autocuidado"),
                "puntaje_cuidado_hogar": request.POST.get("puntaje_cuidado_hogar"),
                "puntaje_trabajo_recreacion": request.POST.get(
                    "puntaje_trabajo_recreacion"
                ),
                "puntaje_compras_dinero": request.POST.get("puntaje_compras_dinero"),
                "puntaje_viajes": request.POST.get("puntaje_viajes"),
                "puntaje_comunicacion": request.POST.get("puntaje_comunicacion"),
                "puntaje_tecnologia": request.POST.get("puntaje_tecnologia"),
            }

            # Combinar campos de texto y puntajes
            defaults = {**campos, **puntajes}

            # Crear o actualizar
            redlatspanish, created = RedLatSpanishResult.objects.update_or_create(
                visita_examen=visita_examen,  # campo de búsqueda
                defaults=defaults,
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Evaluación RedLat Spanish guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la Evaluación RedLat Spanish: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_BettyFerrel(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            campos = {
                k: request.POST.get(k + "_texto", "")
                for k in [
                    "agotamiento",
                    "cambios_alimenticios",
                    "dolor",
                    "cambios_sueno",
                    "salud_fisica_general",
                    "facilidad_enfrentar",
                    "felicidad",
                    "control_vida",
                    "satisfaccion_vida",
                    "concentracion",
                    "utilidad_personal",
                    "angustia_diagnostico",
                    "ansiedad",
                    "depresion",
                    "miedo_otra_enfermedad",
                    "miedo_retroceso",
                    "miedo_avance",
                    "estado_psicologico",
                    "angustia_familiar",
                    "nivel_ayuda",
                    "relaciones_personales",
                    "vida_sexual",
                    "trabajo",
                    "actividades_hogar",
                    "aislamiento",
                    "carga_economica",
                    "estado_social",
                    "actividades_religiosas",
                    "actividades_espirituales_personales",
                    "incertidumbre_futuro",
                    "cambios_positivos",
                    "proposito_vida",
                    "esperanza",
                    "estado_espiritual",
                ]
            }

            # Obtener puntaje total enviado por JS
            puntaje_total = request.POST.get("puntaje_total", 0)
            try:
                puntaje_total = int(puntaje_total)
            except ValueError:
                puntaje_total = 0

            campos["puntaje_total"] = puntaje_total

            # Guardar o actualizar
            bettyferrel, created = BettyFerrelResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=campos
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Examen Calidad de Vida Betty Ferrel guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request, f"❌ Error al guardar el cuestionario Betty Ferrel: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_evaluacion_clinica_CDR(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "cdr_memoria": request.POST.get("cdr_memoria", ""),
                "cdr_orientacion": request.POST.get("cdr_orientacion", ""),
                "cdr_juicio": request.POST.get("cdr_juicio", ""),
                "cdr_comunitarias": request.POST.get("cdr_comunitarias", ""),
                "cdr_pasatiempos": request.POST.get("cdr_pasatiempos", ""),
                "cdr_cuidado": request.POST.get("cdr_cuidado", ""),
                "cdr_global": request.POST.get("cdr_global", ""),
            }

            # Guardar o actualizar
            cdr_result, created = PuntajeCDRResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=campos
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Evaluación clínica CDR guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request, f"❌ Error al guardar la evaluación clínica CDR: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_consentimiento_participante(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "fecha": request.POST.get("fecha"),
                "hora_inicio": request.POST.get("hora_inicio"),
                "investigador": request.POST.get("investigador"),
                "version_consentimiento": request.POST.get("version_consentimiento"),
                "descripcion_proceso": request.POST.get("descripcion_proceso", ""),
                "preguntas": request.POST.get("preguntas", ""),
                "acepta": request.POST.get("acepta"),
                "hora_firma": request.POST.get("hora_firma"),
                "fecha_firma": request.POST.get("fecha_firma"),
                "testigo1": request.POST.get("testigo1", ""),
                "testigo2": request.POST.get("testigo2", ""),
                "copia_entregada": request.POST.get("copia_entregada"),
                "hora_finalizacion": request.POST.get("hora_finalizacion"),
            }

            # Guardar o actualizar
            consentimientoparticipante, created = (
                ConsentimientoInformadoParticipanteResult.objects.update_or_create(
                    visita_examen=visita_examen, defaults=campos
                )
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                "✅ Consentimiento Informado Participante guardado exitosamente.",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request,
                f"❌ Error al guardar el Consentimiento Informado Participante: {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_consentimiento_cuidador(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "fecha": request.POST.get("fecha"),
                "hora_inicio": request.POST.get("hora_inicio"),
                "investigador": request.POST.get("investigador"),
                "nombre_acompanante": request.POST.get("nombre_acompanante"),
                "nombre_participante": request.POST.get("nombre_participante"),
                "version_consentimiento": request.POST.get("version_consentimiento"),
                "descripcion_proceso": request.POST.get("descripcion_proceso", ""),
                "preguntas": request.POST.get("preguntas", ""),
                "acepta": request.POST.get("acepta"),
                "hora_firma": request.POST.get("hora_firma"),
                "fecha_firma": request.POST.get("fecha_firma"),
                "testigo1": request.POST.get("testigo1", ""),
                "testigo2": request.POST.get("testigo2", ""),
                "copia_entregada": request.POST.get("copia_entregada"),
                "hora_finalizacion": request.POST.get("hora_finalizacion"),
            }

            # Guardar o actualizar
            consentimientocuidador, created = (
                ConsentimientoInformadoCuidadorResult.objects.update_or_create(
                    visita_examen=visita_examen, defaults=campos
                )
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Consentimiento Informado Cuidador guardado exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request,
                f"❌ Error al guardar el Consentimiento Informado Cuidador: {str(e)}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_anamnesis_cuidador(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "nombres_apellidos": request.POST.get("nombres_apellidos"),
                "documento": request.POST.get("documento"),
                "lugar_nacimiento": request.POST.get("lugar_nacimiento"),
                "lugar_procedencia": request.POST.get("lugar_procedencia"),
                "edad": request.POST.get("edad"),
                "genero": request.POST.get("genero"),
                "estado_civil": request.POST.get("estado_civil"),
                "relacion": request.POST.get("relacion"),
                "tiempo_acompanando": request.POST.get("tiempo_acompanando"),
                "ocupacion": request.POST.get("ocupacion", ""),
                "escolaridad": request.POST.get("escolaridad", ""),
                "ingresos_hogar": request.POST.get("ingresos_hogar"),
                "estrato": request.POST.get("estrato"),
                "religion": request.POST.get("religion", ""),
                "lateralidad": request.POST.get("lateralidad", ""),
                "convivencia": request.POST.get("convivencia", ""),
                "eps": request.POST.get("eps", ""),
            }

            # Guardar o actualizar
            anamnesis_cuidador, created = (
                AnamnesisCuidadorResult.objects.update_or_create(
                    visita_examen=visita_examen, defaults=campos
                )
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "✅ Anamnesis Cuidador guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(request, f"❌ Error al guardar Anamnesis Cuidador: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_anamnesis_participante(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener visita_examen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            campos = {
                "nombres_apellidos": request.POST.get("nombres_apellidos"),
                "documento": request.POST.get("documento"),
                "lugar_nacimiento": request.POST.get("lugar_nacimiento"),
                "edad": request.POST.get("edad"),
                "sexo": request.POST.get("sexo"),
                "tiempo_acompanando": request.POST.get("tiempo_acompanando"),
                "ingresos_hogar": request.POST.get("ingresos_hogar"),
                "estrato": request.POST.get("estrato"),
                "religion": request.POST.get("religion", ""),
                "lateralidad": request.POST.get("lateralidad", ""),
                "convivencia": request.POST.get("convivencia", ""),
                "eps": request.POST.get("eps", ""),
            }

            # Guardar o actualizar
            anamnesis_participante, created = (
                AnamnesisParticipanteResult.objects.update_or_create(
                    visita_examen=visita_examen, defaults=campos
                )
            )

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Anamnesis Participante guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request, f"❌ Error al guardar la Anamnesis Participante: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_Cuidador_Zarit(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la visita asociada
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener respuestas de las preguntas

            campos = [
                "pide_ayuda",
                "falta_tiempo_propio",
                "agobio",
                "verguenza_conducta",
                "sentir_enfado",
                "afectar_relacion_negativamente",
                "miedo_futuro",
                "dependencia",
                "sentir_tension",
                "deterioro_salud",
                "menos_intimidad",
                "resentir_vida_social",
                "desatender_amistades",
                "unica_dependencia",
                "dinero_insuficiente",
                "incapaz_mas_tiempo",
                "perder_control_vida",
                "cuidado_a_otros",
                "indecision_que_hacer",
                "hacer_mas",
                "cuidar_mejor",
                "grado_carga",
            ]
            # respuestas = {campo+"_value": request.POST.get(campo) for campo in campos}

            respuestas_texto = {
                campo: request.POST.get(campo + "_texto") for campo in campos
            }

            puntaje_total = request.POST.get("puntaje_total")
            interpretacion = request.POST.get("interpretacion")

            zarit, created = ZaritResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # **respuestas,
                    **respuestas_texto,
                    "puntaje_total": puntaje_total,
                    "interpretacion": interpretacion,
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "✅ Escala de Zarit guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si falla
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar la escala de Zarit: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_intervenciones(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la visita asociada
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como en progreso si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Campos del formulario
            numero_sesion = request.POST.get("num_sesion")
            nombre_sesion = request.POST.get("nombre")
            fecha = request.POST.get("fecha")
            hora_inicio = request.POST.get("hora_inicio")
            hora_fin = request.POST.get("hora_fin")
            asistencia = request.POST.get("asistencia")
            participacion = request.POST.get("participacion")
            estado = request.POST.get("estado")
            tematica = request.POST.get("tematica")
            observaciones = request.POST.get("observaciones")

            # Guardar o actualizar la sesión
            sesion, created = SeguimientoIntervencionesResult.objects.update_or_create(
                visita_examen=visita_examen,
                numero_sesion=numero_sesion,
                defaults={
                    "nombre_sesion": nombre_sesion,
                    "fecha": fecha if fecha else None,
                    "hora_inicio": hora_inicio if hora_inicio else None,
                    "hora_fin": hora_fin if hora_fin else None,
                    "asistencia": asistencia,
                    "participacion": participacion if participacion else None,
                    "estado": estado,
                    "tematica": tematica,
                    "observaciones": observaciones,
                },
            )

            # Si ya se completaron todas las sesiones necesarias, puedes marcar la visita como completada.
            # Aquí lo dejamos siempre como en progreso, pero puedes añadir tu propia lógica.
            visita_examen.estado = "en_progreso"
            visita_examen.save()

            if created:
                messages.success(
                    request, f"✅ Sesión {numero_sesion} guardada exitosamente."
                )
            else:
                messages.success(
                    request, f"✅ Sesión {numero_sesion} actualizada exitosamente."
                )

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si falla
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar la sesión: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def obtener_datos_sesion(request, visita_id, examen_id, num_sesion):
    visita_examen = get_object_or_404(
        VisitaExamen, visita_id=visita_id, examen_id=examen_id
    )
    try:
        sesion = SeguimientoIntervencionesResult.objects.get(
            visita_examen=visita_examen, numero_sesion=num_sesion
        )
        data = {
            "nombre": sesion.nombre_sesion,
            "fecha": sesion.fecha.strftime("%Y-%m-%d") if sesion.fecha else "",
            "hora_inicio": sesion.hora_inicio.strftime("%H:%M")
            if sesion.hora_inicio
            else "",
            "hora_fin": sesion.hora_fin.strftime("%H:%M") if sesion.hora_fin else "",
            "asistencia": sesion.asistencia,
            "participacion": sesion.participacion,
            "estado": sesion.estado,
            "tematica": sesion.tematica,
            "observaciones": sesion.observaciones,
        }
    except SeguimientoIntervencionesResult.DoesNotExist:
        data = {}

    return JsonResponse(data)


@login_required
def resumen_sesiones(request, visita_id, examen_id):
    visita_examen = get_object_or_404(
        VisitaExamen, visita_id=visita_id, examen_id=examen_id
    )

    sesiones = SeguimientoIntervencionesResult.objects.filter(
        visita_examen=visita_examen
    ).order_by("numero_sesion")

    if sesiones.count() < 24:
        return JsonResponse({"error": "Aún no se han completado las 24 sesiones."})

    total_sesiones = 24
    asistidas = sesiones.filter(asistencia="Sí").count()

    porcentaje_asistencia = round((asistidas / total_sesiones) * 100, 2)
    conteo_asistencia = f"{asistidas}/{total_sesiones}"

    participaciones = [s.participacion for s in sesiones if s.participacion]
    promedio_participacion = (
        round(sum(map(int, participaciones)) / len(participaciones), 2)
        if participaciones
        else 0
    )

    tendencia_participacion = [
        int(s.participacion) if s.participacion else None for s in sesiones
    ]

    alerta = None
    if porcentaje_asistencia < 70:
        alerta = "⚠️ Riesgo de abandono (asistencia < 70%)"

    data = {
        "porcentaje_asistencia": porcentaje_asistencia,
        "conteo_asistencia": conteo_asistencia,
        "promedio_participacion": promedio_participacion,
        "tendencia_participacion": tendencia_participacion,
        "alerta": alerta,
    }

    return JsonResponse(data)


# Estadísticas - RecuérdaMe


@login_required(login_url="/login/")
@user_passes_test(is_superuser, login_url="/login/")
def estadisticas(request):
    url_query = (
        f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
    )
    headers = {
        "Authorization": f"Bearer {settings.POSTHOG_PERSONAL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        # --------- 1. DAU (TrendsQuery) ---------
        query_dau = {
            "kind": "TrendsQuery",
            "series": [
                {
                    "kind": "EventsNode",
                    "event": "$pageview",
                    "name": "$pageview",
                    "math": "dau",
                }
            ],
            "interval": "day",
            "dateRange": {"date_from": "-30d", "explicitDate": False},
        }

        r1 = requests.post(url_query, headers=headers, json={"query": query_dau})
        r1.raise_for_status()
        data_dau = r1.json()

        dau_labels, dau_values = [], []
        results_dau = data_dau.get("results", [])
        if results_dau:
            dau_labels = results_dau[0].get("labels", [])
            dau_values = results_dau[0].get("data", [])

        # --------- 2. Growth Accounting (LifecycleQuery) ---------
        query_growth = {
            "kind": "LifecycleQuery",
            "series": [
                {"event": "$pageview"}
            ],  # puedes cambiar el evento si quieres otro
            "dateRange": {"date_from": "-30d"},
            "interval": "day",
        }

        r2 = requests.post(url_query, headers=headers, json={"query": query_growth})
        r2.raise_for_status()
        data_growth = r2.json()

        growth_labels, growth_datasets = [], []
        results_growth = data_growth.get("results", [])
        if results_growth:
            # Todas las series comparten las mismas fechas
            growth_labels = results_growth[0].get("days", [])
            for serie in results_growth:
                raw_label = serie.get("label", "")
                clean_label = raw_label.split(" - ")[-1].capitalize()

                # Dejamos los datos tal cual, incluso negativos
                data = serie.get("data", [])

                growth_datasets.append(
                    {
                        "label": clean_label,
                        "data": data,
                    }
                )

        # --------- 3. Device Type (Insight) ---------
        device_labels, device_values = [], []

        # 1. Obtener el insight ya configurado
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_DEVICE_TYPE_INSIGHT_ID}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        # 2. Ejecutar la query del insight
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        results = data.get("results") or data.get("result") or []

        device_translation = {
            "Desktop": "Computador",
            "Mobile": "Celular",
            "Tablet": "Tablet",
        }

        if results:
            for serie in results:
                # label / breakdown del dispositivo
                device = (
                    serie.get("breakdown_value")
                    or serie.get("breakdown")
                    or serie.get("label")
                    or "Otro"
                )
                if isinstance(device, list):
                    device = device[0] if device else "Otro"

                # normalizar al español
                device_name = device_translation.get(device, device)

                # sacar valores → PostHog los devuelve en "data", "result" o "count"
                total = None
                if (
                    "aggregated_value" in serie
                    and serie["aggregated_value"] is not None
                ):
                    total = serie["aggregated_value"]
                elif "count" in serie and serie["count"] is not None:
                    total = serie["count"]
                elif "data" in serie:
                    total = sum(serie.get("data", []))
                elif "result" in serie:
                    vals = serie.get("result", [])
                    if isinstance(vals, list):
                        total = sum(v for v in vals if isinstance(v, (int, float)))

                total = int(total or 0)

                device_labels.append(device_name)
                device_values.append(total)

        # --------- 4. Ingresos por usuario (Login) ---------
        # 1. Traer el insight (para obtener la query)
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_IDENTIFY_COUNT_INSIGHT_ID}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        # 2. Ejecutar la query del insight
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()
        data = r.json()

        # DEBUG: imprime la respuesta cruda (recorta si es muy larga)
        # print("Raw data (first 20000 chars):", json.dumps(data, indent=2)[:20000])

        user_labels, user_values = [], []

        def flatten(x):
            """Generador recursivo que aplana listas anidadas."""
            if isinstance(x, list):
                for el in x:
                    yield from flatten(el)
            else:
                yield x

        def extract_numbers_from_value(v):
            """Dado un elemento v (num, str numérica, dict...), intenta extraer un número."""
            if v is None:
                return None
            # Si es dict, buscar claves típicas
            if isinstance(v, dict):
                for k in (
                    "aggregated_value",
                    "aggregated",
                    "count",
                    "value",
                    "y",
                    "total",
                ):
                    if k in v and v[k] is not None:
                        try:
                            return float(v[k])
                        except Exception:
                            pass
                return None
            # Si es numérico directo
            if isinstance(v, (int, float)):
                return float(v)
            # Si es string que contiene número
            if isinstance(v, str):
                try:
                    return float(v)
                except Exception:
                    return None
            return None

        results = data.get("results") or data.get("result") or []

        if results:
            for idx, serie in enumerate(results):
                # Email / label
                email_field = (
                    serie.get("breakdown_value")
                    or serie.get("breakdown")
                    or serie.get("label")
                    or "Sin label"
                )
                if isinstance(email_field, list):
                    email = email_field[0] if email_field else "Sin email"
                else:
                    email = email_field

                # 1) Priorizar aggregated_value
                total_sum = None
                if (
                    "aggregated_value" in serie
                    and serie.get("aggregated_value") is not None
                ):
                    total_sum = serie.get("aggregated_value")

                # 2) luego count
                if (
                    total_sum in (None, "")
                    and "count" in serie
                    and serie.get("count") is not None
                ):
                    total_sum = serie.get("count")

                # 3) luego buscar arrays con números en keys comunes
                if total_sum in (None, ""):
                    # posibles keys donde PostHog pone los valores por día
                    for key in ("result", "data", "values", "series", "points"):
                        if key in serie and serie.get(key) is not None:
                            vals = serie.get(key)
                            # aplanar y extraer números
                            nums = []
                            for item in flatten(vals):
                                num = extract_numbers_from_value(item)
                                if num is not None:
                                    nums.append(num)
                            if nums:
                                total_sum = sum(nums)
                                break

                # 4) si todavía no hay nada, intentar inspeccionar el propio 'serie' (por si vienen anidados)
                if total_sum in (None, ""):
                    # Buscar cualquier número en los valores del dict serie
                    nums = []
                    for v in serie.values():
                        for item in flatten([v]):
                            num = extract_numbers_from_value(item)
                            if num is not None:
                                nums.append(num)
                    if nums:
                        total_sum = sum(nums)

                # Normalizar total_sum a int (0 si no se encontró)
                try:
                    total_sum = int(total_sum) if total_sum is not None else 0
                except Exception:
                    try:
                        total_sum = int(float(total_sum))
                    except Exception:
                        total_sum = 0

                # Guardar si es email válido (o si quieres mostrar otros breakdowns, ajusta aquí)
                if isinstance(email, str) and "@" in email:
                    user_labels.append(email)
                    user_values.append(total_sum)

        # --------- 5. Sesiones (Pageview -> Pageleave) ---------
        session_rows = []

        # 1. Traer el insight
        url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_SESION_TIME_INSIGHT_ID}/"
        r = requests.get(url_insight, headers=headers)
        r.raise_for_status()
        insight = r.json()

        # 2. Ejecutar la query
        query = insight.get("query")
        url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
        r = requests.post(url_query, headers=headers, json={"query": query})
        r.raise_for_status()

        data = r.json()
        # print("=== RAW DATA FROM POSTHOG ===")
        # print(json.dumps(data, indent=2))  # imprime en consola el JSON completo

        # 🔹 Extraer resultados: manejar funnels que devuelven "steps"
        if isinstance(data, dict):
            results = (
                data.get("steps") or data.get("results") or data.get("result") or []
            )
        elif isinstance(data, list):
            results = data
        else:
            results = []

        def safe_num(x):
            try:
                return float(x)
            except Exception:
                return None

        def format_seconds(seconds):
            if not seconds:
                return None
            seconds = int(seconds)
            m, s = divmod(seconds, 60)
            if m > 0:
                return f"{m}m {s}s"
            return f"{s}s"

        # 3. Iterar sobre cada step del funnel
        for serie in results:
            # A veces viene en lista
            if isinstance(serie, list) and serie:
                last = serie[-1]  # leavepage
                first = serie[0]  # viewpage
            elif isinstance(serie, dict):
                first = last = serie
            else:
                continue

            # 🔹 Identificar usuario/email/breakdown
            email_field = (
                last.get("breakdown_value")
                or last.get("breakdown")
                or last.get("label")
                or "Sin dato"
            )
            if isinstance(email_field, list):
                email = email_field[0] if email_field else "Sin dato"
            else:
                email = email_field

            entered = safe_num(first.get("count")) or 0
            converted = safe_num(last.get("count")) or 0
            dropped = max(entered - converted, 0)

            session_rows.append(
                {
                    "email": email,
                    # "raw_keys": ", ".join(serie.keys()),
                    # "step": step_name,
                    "entered": int(entered),
                    "converted": converted,
                    "dropped_off": int(dropped),
                    "conversion_rate": round((converted / entered) * 100, 2)
                    if entered > 0
                    else 0,
                    "avg_time": format_seconds(last.get("average_conversion_time")),
                    "median_time": format_seconds(last.get("median_conversion_time")),
                }
            )

            # --------- 6. Conteo de vistas por página ---------

            views_labels, views_values = [], []

            # 1. Traer el insight
            url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_VIEWS_PER_PAGE}/"
            r = requests.get(url_insight, headers=headers)
            r.raise_for_status()
            insight = r.json()

            # 2. Ejecutar la query del insight
            query = insight.get("query")
            url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
            r = requests.post(url_query, headers=headers, json={"query": query})
            r.raise_for_status()
            data = r.json()

            # DEBUG opcional
            # print("=== RAW DATA (Vistas por página) ===")
            # print(json.dumps(data, indent=2)[:20000])

            results = []

            if isinstance(data, dict):
                if "results" in data and isinstance(data["results"], list):
                    results = data["results"]
                elif "result" in data and isinstance(data["result"], list):
                    results = data["result"]
                elif "data" in data and isinstance(data["data"], list):
                    results = data["data"]
            elif isinstance(data, list):
                results = data

            if results:
                # print("=== KEYS EN RESULTS ===")
                # for idx, serie in enumerate(results):
                #     print(f"Serie {idx}: keys={list(serie.keys())}")
                #     print(" Sample:", json.dumps(serie, indent=2)[:500])

                for idx, serie in enumerate(results):
                    # Nombre de la sección
                    section = serie.get("order")

                    # Total de vistas
                    total = None
                    if (
                        "aggregated_value" in serie
                        and serie["aggregated_value"] is not None
                    ):
                        total = serie["aggregated_value"]

                    total = int(total or 0)

                    # print(f"Sección: {section} → {total}")  # DEBUG

                    views_labels.append(section)
                    views_values.append(total)

            # Construir dataset en formato Chart.js
            views_dataset = [
                {
                    "label": views_labels,
                    "data": views_values,
                }
            ]

            # --------- 7. Vistas por página con breakdown por email ---------
            # 1. Variables de salida
            user_views_labels, views_matrix = [], []
            emails_set = set()

            # 2. Traer el insight desde PostHog
            url_insight = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_PAGES_VIEWS_PER_USER}/"
            r = requests.get(url_insight, headers=headers)
            r.raise_for_status()
            insight = r.json()

            # 3. Ejecutar la query del insight
            query = insight.get("query")
            url_query = f"{settings.POSTHOG_API_URL}/api/projects/{settings.POSTHOG_PROJECT_ID}/query/"
            r = requests.post(url_query, headers=headers, json={"query": query})
            r.raise_for_status()
            data = r.json()

            results = data.get("results") or data.get("result") or []

            user_page_views = {}

            if results:
                for serie in results:
                    # Email
                    email_field = (
                        serie.get("breakdown_value")
                        or serie.get("breakdown")
                        or serie.get("label")
                        or "Sin email"
                    )
                    if isinstance(email_field, list):
                        email = email_field[0] if email_field else "Sin email"
                    else:
                        email = email_field

                    page_raw = serie.get("order") or serie.get("page") or 0
                    try:
                        page = int(page_raw)
                    except Exception:
                        page = page_raw

                    # Conteo
                    total = 0
                    if (
                        "aggregated_value" in serie
                        and serie["aggregated_value"] is not None
                    ):
                        total = int(serie["aggregated_value"] or 0)

                    # Guardar
                    emails_set.add(email)
                    if email not in user_page_views:
                        user_page_views[email] = {}
                    user_page_views[email][page] = total

            # 5. Ordenar y preparar labels/filas
            emails_sorted = sorted(list(emails_set))

            label_map = {
                0: "Sección: Información en Salud",
                1: "Sección: Pasatiempos",
                2: "Sección: Encuentros",
                3: "Sección: Fortalece tu mente",
                4: "Sección: Hazlo consciente",
                5: "Hazlo Consciente - Módulo 2",
                6: "Hazlo Consciente - Módulo 3",
                7: "Hazlo Consciente - Módulo 4",
                8: "Pasatiempos - Plantas",
                9: "Pasatiempos - Mascotas",
                10: "Pasatiempos - Recetas",
                11: "Pasatiempos - Ejercicio",
                12: "Polijuego",
            }

            # --- 2. Forzar que siempre existan todas las páginas del 0 al 12 ---
            all_pages = list(range(0, 13))

            # --- 3. Labels visibles para la tabla ---
            user_views_labels = [label_map[p] for p in all_pages]

            # matriz final
            views_matrix = []
            for email in emails_sorted:
                row = {"email": email}
                for page in all_pages:
                    row[label_map[page]] = user_page_views.get(email, {}).get(page, 0)
                views_matrix.append(row)

        # 5. Renderizar template
        return render(
            request,
            "home/statistics_recuerdame.html",
            {
                "labels": dau_labels,
                "values": dau_values,
                "growth_labels": growth_labels,
                "growth_datasets": growth_datasets,
                "device_labels": device_labels,
                "device_values": device_values,
                "user_labels": user_labels,
                "user_values": user_values,
                "session_rows": session_rows,
                "views_labels": views_labels,
                "views_dataset": views_dataset,
                "views_labels_breakdown": user_views_labels,
                "views_matrix": views_matrix,
            },
        )

    except requests.exceptions.RequestException as e:
        return HttpResponseServerError(f"Error al obtener datos: {e}")


#######################################################################################


@login_required
def guardar_examen_analisis(request):
    if request.method == "POST":
        try:
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # Obtener datos principales
            analisis_historia = request.POST.get("analisis_historia", "")
            plan_tratamiento = request.POST.get("plan_tratamiento", "")

            # Crear o actualizar resultado principal
            analisis_result, created = AnalisisGeneralResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "analisis_historia": analisis_historia,
                    "plan_tratamiento": plan_tratamiento,
                },
            )

            # Limpiar diagnósticos existentes
            analisis_result.diagnosticos_cie10.all().delete()
            analisis_result.diagnosticos_dsmv.all().delete()
            analisis_result.diagnosticos_icsd3.all().delete()
            analisis_result.diagnosticos_no_clasificados.all().delete()

            # Procesar diagnósticos CIE-10
            cie10_codigos = request.POST.getlist("cie10_codigo[]")
            cie10_diagnosticos = request.POST.getlist("cie10_diagnostico[]")
            cie10_estados = request.POST.getlist("cie10_estado[]")

            for i, (codigo, diagnostico) in enumerate(
                zip(cie10_codigos, cie10_diagnosticos)
            ):
                if codigo.strip() and diagnostico.strip():
                    # Crear el diagnóstico
                    diag_cie10 = DiagnosticoCIE10.objects.create(
                        analisis_result=analisis_result,
                        codigo=codigo.strip(),
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    # Marcar estados correspondientes basados en los checkboxes
                    if "confirmado_nuevo" in cie10_estados:
                        diag_cie10.confirmado_nuevo = True
                    if "confirmado_antiguo" in cie10_estados:
                        diag_cie10.confirmado_antiguo = True
                    if "en_estudio" in cie10_estados:
                        diag_cie10.en_estudio = True

                    diag_cie10.save()

            # Procesar diagnósticos DSM-V (similar estructura)
            dsmv_codigos = request.POST.getlist("dsmv_codigo[]")
            dsmv_diagnosticos = request.POST.getlist("dsmv_diagnostico[]")
            dsmv_estados = request.POST.getlist("dsmv_estado[]")

            for i, (codigo, diagnostico) in enumerate(
                zip(dsmv_codigos, dsmv_diagnosticos)
            ):
                if codigo.strip() and diagnostico.strip():
                    diag_dsmv = DiagnosticoDSMV.objects.create(
                        analisis_result=analisis_result,
                        codigo=codigo.strip(),
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    if "confirmado_nuevo" in dsmv_estados:
                        diag_dsmv.confirmado_nuevo = True
                    if "confirmado_antiguo" in dsmv_estados:
                        diag_dsmv.confirmado_antiguo = True
                    if "en_estudio" in dsmv_estados:
                        diag_dsmv.en_estudio = True

                    diag_dsmv.save()

            # Procesar diagnósticos ICSD-3 (similar estructura)
            icsd3_codigos = request.POST.getlist("icsd3_codigo[]")
            icsd3_diagnosticos = request.POST.getlist("icsd3_diagnostico[]")
            icsd3_estados = request.POST.getlist("icsd3_estado[]")

            for i, (codigo, diagnostico) in enumerate(
                zip(icsd3_codigos, icsd3_diagnosticos)
            ):
                if codigo.strip() and diagnostico.strip():
                    diag_icsd3 = DiagnosticoICSD3.objects.create(
                        analisis_result=analisis_result,
                        codigo=codigo.strip(),
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    if "confirmado_nuevo" in icsd3_estados:
                        diag_icsd3.confirmado_nuevo = True
                    if "confirmado_antiguo" in icsd3_estados:
                        diag_icsd3.confirmado_antiguo = True
                    if "en_estudio" in icsd3_estados:
                        diag_icsd3.en_estudio = True

                    diag_icsd3.save()

            # Procesar diagnósticos no clasificados
            noclasi_diagnosticos = request.POST.getlist("noclasi_diagnostico[]")
            noclasi_estados = request.POST.getlist("noclasi_estado[]")

            for i, diagnostico in enumerate(noclasi_diagnosticos):
                if diagnostico.strip():
                    diag_noclasi = DiagnosticoNoClasificado.objects.create(
                        analisis_result=analisis_result,
                        diagnostico=diagnostico.strip(),
                        orden=i + 1,
                    )

                    if "confirmado_nuevo" in noclasi_estados:
                        diag_noclasi.confirmado_nuevo = True
                    if "confirmado_antiguo" in noclasi_estados:
                        diag_noclasi.confirmado_antiguo = True
                    if "en_estudio" in noclasi_estados:
                        diag_noclasi.en_estudio = True

                    diag_noclasi.save()

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Contar diagnósticos guardados
            total_diagnosticos = (
                analisis_result.diagnosticos_cie10.count()
                + analisis_result.diagnosticos_dsmv.count()
                + analisis_result.diagnosticos_icsd3.count()
                + analisis_result.diagnosticos_no_clasificados.count()
            )

            messages.success(
                request,
                f"✅ Análisis y diagnósticos guardados exitosamente.\n"
                f"📋 Total de diagnósticos: {total_diagnosticos}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"❌ Error al guardar el análisis: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")


@login_required
def guardar_examen_antecedentes(request):
    if request.method == "POST":
        try:
            print("=== REQUEST.POST ===")
            visita_id = request.POST.get("visita_id")
            paciente_id = request.POST.get("paciente_id")
            examen_id = request.POST.get("examen_id")

            # Obtener la instancia de VisitaExamen
            visita_examen = get_object_or_404(
                VisitaExamen, visita_id=visita_id, examen_id=examen_id
            )

            # Obtener el paciente
            paciente = get_object_or_404(DatosDemograficos, id=paciente_id)

            # Marcar como iniciado si está pendiente
            if visita_examen.estado == "pendiente":
                visita_examen.estado = "en_progreso"
                visita_examen.fecha_inicio = timezone.now()
                visita_examen.save()

            # NUEVO: Obtener o crear antecedentes únicos por paciente
            antecedentes_result, created = AntecedentesResult.get_or_create_for_patient(
                paciente=paciente, visita_examen=visita_examen, usuario=request.user
            )

            # Actualizar observaciones generales
            antecedentes_result.observaciones_generales = request.POST.get(
                "observaciones_generales", ""
            )

            # Crear o actualizar el link de la visita
            visita_link, link_created = AntecedentesVisitaLink.objects.get_or_create(
                visita_examen=visita_examen,
                defaults={"antecedentes_result": antecedentes_result},
            )
            visita_link.fue_revisado = True
            visita_link.fue_actualizado = True
            visita_link.revisado_por = request.user.username
            visita_link.save()

            # Variable para controlar si hay algún antecedente
            tiene_antecedentes = False
            antecedentes_guardados = []

            # ===== PROCESAR ANTECEDENTES DINÁMICOS =====
            # Obtener datos de antecedentes dinámicos (desde JavaScript)
            patologicos_data = request.POST.get("patologicos_data")
            quirurgicos_data = request.POST.get("quirurgicos_data")
            print("Quirúrgicos data:", quirurgicos_data)  # DEBUG
            farmacologicos_data = request.POST.get("farmacologicos_data")
            toxicos_data = request.POST.get("toxicos_data")
            familiares_data = request.POST.get("familiares_data")
            alergicos_data = request.POST.get("alergicos_data")
            traumaticos_data = request.POST.get("traumaticos_data")
            gineco_data = request.POST.get("gineco_data")
            epidemiologicos_data = request.POST.get("epidemiologicos_data")
            ets_data = request.POST.get("ets_data")
            hospitalizaciones_data = request.POST.get("hospitalizaciones_data")
            print("Hospitalizaciones data:", hospitalizaciones_data)  # DEBUG
            inmunizaciones_data = request.POST.get("inmunizaciones_data")
            transfusionales_data = request.POST.get("transfusionales_data")

            # ===== PROCESAR PATOLÓGICOS =====
            if patologicos_data:
                patologicos_list = json.loads(patologicos_data)
                # Limpiar existentes
                antecedentes_result.antecedentes_patologicos.all().delete()

                for item in patologicos_list:
                    if item.get("tipo_patologia"):
                        tiene_antecedentes = True
                        AntecedentePatologico.objects.create(
                            antecedente_result=antecedentes_result,
                            tipo_patologia=item.get("tipo_patologia", "otros"),
                            descripcion_otros=item.get("descripcion_otros")
                            if item.get("tipo_patologia") == "otros"
                            else None,
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            ha_recibido_tratamiento=item.get(
                                "ha_recibido_tratamiento", False
                            ),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            tiene_complicaciones=item.get(
                                "tiene_complicaciones", False
                            ),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if patologicos_list:
                    antecedentes_guardados.append("Patológicos")

            # ===== PROCESAR QUIRÚRGICOS =====
            if quirurgicos_data:
                quirurgicos_list = json.loads(quirurgicos_data)
                antecedentes_result.antecedentes_quirurgicos.all().delete()
                for item in quirurgicos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteQuirurgico.objects.create(
                            antecedente_result=antecedentes_result,
                            descripcion=item.get("descripcion"),
                            fecha_intervencion=datetime.strptime(
                                item.get("fecha_intervencion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_intervencion")
                            else None,
                            ha_recibido_tratamiento=item.get(
                                "ha_recibido_tratamiento", False
                            ),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            tiene_complicaciones=item.get(
                                "tiene_complicaciones", False
                            ),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if quirurgicos_list:
                    antecedentes_guardados.append("Quirúrgicos")

            # ===== PROCESAR FARMACOLÓGICOS =====
            if farmacologicos_data:
                farmacologicos_list = json.loads(farmacologicos_data)
                antecedentes_result.antecedentes_farmacologicos.all().delete()

                for item in farmacologicos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteFarmacologico.objects.create(
                            antecedente_result=antecedentes_result,
                            descripcion=item.get("descripcion"),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            recibio_tratamiento=item.get("recibio_tratamiento", False),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            tuvo_complicaciones=item.get("tuvo_complicaciones", False),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if farmacologicos_list:
                    antecedentes_guardados.append("Farmacológicos")

            # ===== PROCESAR TÓXICOS =====
            if toxicos_data:
                toxicos_list = json.loads(toxicos_data)
                print("Tóxicos list:", toxicos_list)  # DEBUG
                antecedentes_result.antecedentes_toxicos.all().delete()

                for item in toxicos_list:
                    if item.get("tipos_toxico"):
                        print("Procesando tóxico:", item)  # DEBUG
                        tiene_antecedentes = True
                        AntecedenteToxico.objects.create(
                            antecedente_result=antecedentes_result,
                            tipos_toxico=item.get("tipos_toxico", []),
                            descripcion_otros=item.get("descripcion_otros", ""),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            ha_recibido_tratamiento=item.get(
                                "ha_recibido_tratamiento", False
                            ),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            tiene_complicaciones=item.get(
                                "tiene_complicaciones", False
                            ),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if toxicos_list:
                    antecedentes_guardados.append("Tóxicos")

            # ===== PROCESAR FAMILIARES =====
            if familiares_data:
                familiares_list = json.loads(familiares_data)
                antecedentes_result.antecedentes_familiares.all().delete()

                for item in familiares_list:
                    if item.get("tipo_antecedente") and item.get("parentesco"):
                        tiene_antecedentes = True
                        AntecedenteFamiliar.objects.create(
                            antecedente_result=antecedentes_result,
                            tipo_antecedente=item.get("tipo_antecedente"),
                            parentesco=item.get("parentesco"),
                            observaciones=item.get("observaciones", ""),
                        )
                if familiares_list:
                    antecedentes_guardados.append("Familiares")

            # ===== PROCESAR ALÉRGICOS =====
            if alergicos_data:
                alergicos_list = json.loads(alergicos_data)
                antecedentes_result.antecedentes_alergicos.all().delete()

                for item in alergicos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteAlergico.objects.create(
                            antecedente_result=antecedentes_result,
                            descripcion=item.get("descripcion"),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            tratamiento_recibido=item.get("tratamiento_recibido", ""),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            complicaciones=item.get("complicaciones", ""),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if alergicos_list:
                    antecedentes_guardados.append("Alérgicos")

            # ===== PROCESAR TRAUMÁTICOS =====
            if traumaticos_data:
                traumaticos_list = json.loads(traumaticos_data)
                antecedentes_result.antecedentes_traumaticos.all().delete()

                for item in traumaticos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteTraumatico.objects.create(
                            antecedente_result=antecedentes_result,
                            descripcion=item.get("descripcion"),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            tratamiento_recibido=item.get("tratamiento_recibido", ""),
                            detalle_tratamiento=item.get("detalle_tratamiento", ""),
                            complicaciones=item.get("complicaciones", ""),
                            activo=item.get("activo", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if traumaticos_list:
                    antecedentes_guardados.append("Traumáticos")

            # ===== PROCESAR GINECO-OBSTÉTRICOS =====
            if gineco_data:
                gineco_dict = json.loads(gineco_data)
                # Eliminar existente (OneToOne)
                if hasattr(antecedentes_result, "antecedentes_gineco"):
                    antecedentes_result.antecedentes_gineco.delete()

                if gineco_dict:
                    tiene_antecedentes = True
                    AntecedenteGinecoObstetrico.objects.create(
                        antecedente_result=antecedentes_result,
                        tiene_menarquia=gineco_dict.get("tiene_menarquia", False),
                        edad_menarquia=gineco_dict.get("edad_menarquia"),
                        tiene_menopausia=gineco_dict.get("tiene_menopausia", False),
                        edad_menopausia=gineco_dict.get("edad_menopausia"),
                        gravidez=gineco_dict.get("gravidez", 0),
                        abortos=gineco_dict.get("abortos", 0),
                        hijos_vivos=gineco_dict.get("hijos_vivos", 0),
                        usa_metodo_planificacion=gineco_dict.get(
                            "usa_metodo_planificacion", False
                        ),
                        metodo_detalle=gineco_dict.get("metodo_detalle", ""),
                        dosis_planificacion=gineco_dict.get("dosis_planificacion", ""),
                        adherencia_planificacion=gineco_dict.get(
                            "adherencia_planificacion", ""
                        ),
                        tolerancia_planificacion=gineco_dict.get(
                            "tolerancia_planificacion", ""
                        ),
                        observaciones=gineco_dict.get("observaciones", ""),
                    )
                    antecedentes_guardados.append("Gineco-Obstétricos")

            # ===== PROCESAR EPIDEMIOLÓGICOS (NUEVO) =====
            if epidemiologicos_data:
                epidemiologicos_list = json.loads(epidemiologicos_data)
                antecedentes_result.antecedentes_epidemiologicos.all().delete()

                for item in epidemiologicos_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteEpidemiologico.objects.create(
                            antecedente_result=antecedentes_result,
                            tipo_antecedente=item.get("descripcion"),
                            fecha_inicio=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            tratamiento_detalle=item.get("tratamiento_detalle", ""),
                            complicaciones_asociadas=item.get(
                                "complicaciones_asociadas", False
                            ),
                            detallar_complicaciones=item.get(
                                "detallar_complicaciones", ""
                            ),
                            activo_actualmente=item.get("activo_actualmente", True),
                            fecha_finalizacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if epidemiologicos_list:
                    antecedentes_guardados.append("Epidemiológicos")

            # ===== PROCESAR ETS (NUEVO) =====
            if ets_data:
                ets_list = json.loads(ets_data)
                antecedentes_result.antecedentes_ets.all().delete()

                for item in ets_list:
                    if item.get("descripcion"):
                        tiene_antecedentes = True
                        AntecedenteETS.objects.create(
                            antecedente_result=antecedentes_result,
                            tipo_ets=item.get("descripcion"),
                            fecha_diagnostico=datetime.strptime(
                                item.get("fecha_inicio"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_inicio")
                            else None,
                            tratamiento_recibido=item.get(
                                "ha_recibido_tratamiento", False
                            ),
                            detalle_tratamiento=item.get("tratamiento_detalle", ""),
                            complicaciones=item.get("complicaciones_asociadas", False),
                            detalle_complicaciones=item.get(
                                "detallar_complicaciones", ""
                            ),
                            curado=not item.get("activo_actualmente", True),
                            fecha_curacion=datetime.strptime(
                                item.get("fecha_finalizacion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_finalizacion")
                            else None,
                            observaciones=item.get("observaciones", ""),
                        )
                if ets_list:
                    antecedentes_guardados.append("ETS")

            # ===== PROCESAR HOSPITALIZACIONES (NUEVO) =====
            # ...existing code...
            if hospitalizaciones_data:
                hospitalizaciones_list = json.loads(hospitalizaciones_data)
                print("Hospitalizaciones list:", hospitalizaciones_list)  # DEBUG
                antecedentes_result.antecedentes_hospitalizaciones.all().delete()

                for item in hospitalizaciones_list:
                    if item.get(
                        "motivo_hospitalizacion"
                    ):  # Cambio: usar el nombre correcto del campo
                        tiene_antecedentes = True

                        # Manejar fecha_egreso de forma segura
                        fecha_egreso = None
                        if item.get("fecha_egreso"):
                            try:
                                fecha_egreso = datetime.strptime(
                                    item.get("fecha_egreso"), "%Y-%m-%d"
                                ).date()
                            except (ValueError, TypeError):
                                fecha_egreso = None

                        # Manejar fecha_ingreso de forma segura
                        fecha_ingreso = None
                        if item.get("fecha_ingreso"):
                            try:
                                fecha_ingreso = datetime.strptime(
                                    item.get("fecha_ingreso"), "%Y-%m-%d"
                                ).date()
                            except (ValueError, TypeError):
                                fecha_ingreso = None

                        # Convertir días_hospitalizacion a entero de forma segura
                        dias_hospitalizacion = None
                        if item.get("dias_hospitalizacion"):
                            try:
                                dias_hospitalizacion = int(
                                    item.get("dias_hospitalizacion")
                                )
                            except (ValueError, TypeError):
                                dias_hospitalizacion = None

                        AntecedenteHospitalizacion.objects.create(
                            antecedente_result=antecedentes_result,
                            motivo_hospitalizacion=item.get("motivo_hospitalizacion"),
                            fecha_ingreso=fecha_ingreso,
                            fecha_egreso=fecha_egreso,
                            institucion=item.get("institucion", ""),
                            dias_hospitalizacion=dias_hospitalizacion,
                            complicaciones_durante=item.get(
                                "complicaciones_durante", False
                            ),
                            detalle_complicaciones=item.get(
                                "detalle_complicaciones", ""
                            ),
                            secuelas=item.get("secuelas", False),
                            detalle_secuelas=item.get("detalle_secuelas", ""),
                            observaciones=item.get("observaciones", ""),
                        )
                if hospitalizaciones_list:
                    antecedentes_guardados.append("Hospitalizaciones")
            # ===== PROCESAR INMUNIZACIONES (NUEVO) =====
            if inmunizaciones_data:
                inmunizaciones_list = json.loads(inmunizaciones_data)
                antecedentes_result.antecedentes_inmunizaciones.all().delete()

                for item in inmunizaciones_list:
                    if item.get("vacuna_inmunizacion"):
                        tiene_antecedentes = True
                        AntecedenteInmunizacion.objects.create(
                            antecedente_result=antecedentes_result,
                            nombre_vacuna=item.get("vacuna_inmunizacion"),
                            fecha_aplicacion=datetime.strptime(
                                item.get("fecha_ultima_dosis"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_ultima_dosis")
                            else None,
                            dosis_numero=item.get("numero_dosis", 1),
                            observaciones=item.get("observaciones", ""),
                        )
                if inmunizaciones_list:
                    antecedentes_guardados.append("Inmunizaciones")

            # ===== PROCESAR TRANSFUSIONALES (NUEVO) =====
            if transfusionales_data:
                transfusionales_list = json.loads(transfusionales_data)
                antecedentes_result.antecedentes_transfusionales.all().delete()

                for item in transfusionales_list:
                    if item.get("motivo_transfusion"):
                        tiene_antecedentes = True
                        AntecedenteTransfusional.objects.create(
                            antecedente_result=antecedentes_result,
                            motivo_transfusion=item.get("motivo_transfusion"),
                            fecha_transfusion=datetime.strptime(
                                item.get("fecha_ultima_transfusion"), "%Y-%m-%d"
                            ).date()
                            if item.get("fecha_ultima_transfusion")
                            else None,
                            tipo_componente=item.get("tipo_componente", "sangre_total"),
                            cantidad_unidades=item.get("numero_unidades", 1),
                            tuvo_reacciones=item.get("tuvo_reacciones", False),
                            detalle_reacciones=item.get("detalle_reacciones", ""),
                            observaciones=item.get("observaciones", ""),
                        )
                if transfusionales_list:
                    antecedentes_guardados.append("Transfusionales")

            # Actualizar el campo principal
            antecedentes_result.tiene_antecedentes = tiene_antecedentes
            antecedentes_result.save()

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            # Mensaje de éxito personalizado
            if antecedentes_guardados:
                tipos_guardados = ", ".join(antecedentes_guardados)
                messages.success(
                    request,
                    f"✅ Antecedentes médicos guardados exitosamente.\n"
                    f"📋 Tipos registrados: {tipos_guardados}",
                )
            else:
                messages.success(
                    request,
                    "✅ Antecedentes médicos guardados exitosamente.\n"
                    "📋 Sin antecedentes registrados.",
                )

            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar los antecedentes médicos: {str(e)}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
        messages.error(request, "❌ Método no permitido.")
        return redirect("index")

        return redirect("proyectos")

    return render(request, "home/proyectos.html", context)
