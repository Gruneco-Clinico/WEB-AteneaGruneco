# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader
from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from .models import (
    DatosDemograficos,
    Proyecto,
    Examen,
    Visita,
    VisitaExamen,
    TipoVisita,
    SuenoAnamnesisResult,
    SuenoFisicoResult,
    SustanciaSueno,
    SintomaSueno,
    PantallaSueno,
    TipoQuejaSueno,
    MedicamentoSueno,
    SintomaDiurnoSueno,
    ActividadEnCamaSueno,
    AtenasResult,
    ActividadFisicaSueno,
    PittsburghResult,
    EpworthResult,
    StopBangResult,
    MEWResult,
    BerlinResult,
    ISIResult,
    EuroQol5D5LResult,
    EuroQolEVASaludResult,
    ParticipanteYesavageResult,
    CuidadorNPIResult,
    LawtonBrodyResult,
    MoCAResult,
    AdherenciaTerapeuticaResult,
    ZaritResult,
    AQDCuidadorResult,
    AQDParticipanteResult,
    RedLatSpanishResult,
    CDRCuidadorResult,
    CDRParticipanteResult
)
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
def estadisticas(request):
    context = {"segment": "estadisticas"}
    html_template = loader.get_template("home/stadistic.html")
    return HttpResponse(html_template.render(context, request))


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
        3: {"template": "examenes_general/General_ExamenFísico.html", "model": None},
        4: {
            "template": "examenes_general/General_RevisiónSistemas.html",
            "model": None,
        },
        5: {"template": "examenes_general/General_Antecedentes.html", "model": None},
        7: {"template": "examenes_general/General_Análisis.html", "model": None},
        8: {"template": "examenes_general/General_Medicamentos.html", "model": None},
        9: {
            "template": "examenes_general/General_ExamenNeurológico.html",
            "model": None,
        },
        10: {
            "template": "examenes_sueno/Sueno_anamnesis.html",
            "model": SuenoAnamnesisResult,
        },
        11: {"template": "examenes_sueno/Sueño_Cuestionarios.html", "model": None},
        12: {
            "template": "examenes_sueno/Sueño_ExamenFisico.html",
            "model": SuenoFisicoResult,
        },  # CORREGIDO: Era el examen físico, no Pittsburgh
        13: {
            "template": "examenes_sueno/sueno_Pitsburg.html",
            "model": PittsburghResult,
        },  # CORREGIDO: Este es Pittsburgh
        14: {"template": "examenes_sueno/sueno_Epworth.html", "model": EpworthResult},
        15: {"template": "examenes_sueno/sueno_Stop_Bang.html","model": StopBangResult,},
        16: {"template": "examenes_sueno/sueno_MEW.html", "model": MEWResult},
        17: {"template": "examenes_sueno/sueno_Berlín.html", "model": BerlinResult},
        18: {"template": "examenes_sueno/sueno_atenas.html", "model": AtenasResult},
        19: {"template": "examenes_sueno/sueno_ISI.html", "model": ISIResult},
        21: {"template": "examenes_anosognosia/Anosognosia_Participante_EuroQoL.html", "model": EuroQol5D5LResult},
        22: {"template": "examenes_anosognosia/Anosognosia_Participante_EVA_EuroQoL.html", "model": EuroQolEVASaludResult},
        23: {"template": "examenes_anosognosia/Anosognosia_Participante_Yesavage.html", "model": ParticipanteYesavageResult},
        24: {"template": "examenes_anosognosia/Anosognosia_Cuidador_NPI.html", "model": CuidadorNPIResult},
        25: {"template": "examenes_anosognosia/Anosognosia_Cuidador_LawtonBrody.html", "model": LawtonBrodyResult},
        #26: {"template": "examenes_anosognosia/Anosognosia_Cuidador_BettyFerrel.html", "model": EuroQol5D5LResult},
        27: {"template": "examenes_anosognosia/Anosognosia_Participante_MoCA.html", "model": MoCAResult},
        28: {"template": "examenes_anosognosia/Anosognosia_Participante_AdherenciaTerapeutica.html", "model": AdherenciaTerapeuticaResult},
        29: {"template": "examenes_anosognosia/Anosognosia_Cuidador_EscalaZarit.html", "model": ZaritResult},
        30: {"template": "examenes_anosognosia/Anosognosia_Cuidador_AQD.html", "model": AQDCuidadorResult},
        31: {"template": "examenes_anosognosia/Anosognosia_Participante_AQD.html", "model": AQDParticipanteResult},
        32: {"template": "examenes_anosognosia/Anosognosia_Cuidador_RedLatSpanish.html", "model": RedLatSpanishResult},
        33: {"template": "examenes_anosognosia/Anosognosia_Cuidador_CDR.html", "model": CDRCuidadorResult},
        34: {"template": "examenes_anosognosia/Anosognosia_Participante_CDR.html", "model": CDRParticipanteResult},

    }

    config = exam_config.get(int(examen_id))  # CAMBIO: Asegurar que sea entero
    if not config:
        messages.error(request, "Examen no encontrado")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    # Obtener datos existentes usando los nuevos métodos
    datos_examen = None
    visita_examen_obj = None
    modo_edicion = False

    try:
        visita_examen_obj = VisitaExamen.objects.get(
            visita_id=visita_id, examen_id=examen_id
        )

        # CAMBIO: Usar el nuevo método get_resultado_instance()
        if config["model"] and visita_examen_obj.esta_realizado:
            resultado = visita_examen_obj.get_resultado_instance()
            if resultado and isinstance(resultado, config["model"]):
                datos_examen = model_to_dict(resultado)
                # Limpiar campos que no necesitas en el template
                datos_examen.pop("id", None)
                datos_examen.pop("visita_examen", None)
                modo_edicion = True

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
        "EuroQol5D5LResult":"examenes_resultados/resultado_euroqol5d5l.html",
        "EuroQolEVASaludResult":"examenes_resultados/resultado_evaeuroqol5d5l.html",
        "ParticipanteYesavageResult":"examenes_resultados/resultado_yesavage.html",
        "CuidadorNPIResult":"examenes_resultados/resultado_npi.html",
        "LawtonBrodyResult":"examenes_resultados/resultado_lawtonbrody.html",
        "MoCAResult":"examenes_resultados/resultado_moca.html",
        "AdherenciaTerapeuticaResult":"examenes_resultados/resultado_adherenciaterapeutica.html",
        "ZaritResult":"examenes_resultados/resultado_zarit.html",
        "AQDCuidadorResult":"examenes_resultados/resultado_aqdcuidador.html",
        "AQDParticipanteResult":"examenes_resultados/resultado_aqdparticipante.html",
        "RedLatSpanishResult":"examenes_resultados/resultado_redlatspanish.html",
        "CDRCuidadorResult":"examenes_resultados/resultado_cdrcuidador.html",
        "CDRParticipanteResult":"examenes_resultados/resultado_cdrparticipante.html",
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

            # Crear o actualizar el resultado de anamnesis de sueño
            anamnesis, created = SuenoAnamnesisResult.objects.get_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Motivo de consulta
                    "motivo_consulta": request.POST.get("motivo_consulta", ""),
                    # Enfermedad actual
                    "enfermedad_actual": request.POST.get("enfermedad_actual", ""),
                    # Antecedentes del sueño
                    "inicio_problemas_sueno": request.POST.get(
                        "inicio_problemas_sueno", ""
                    ),
                    "factor_desencadenante": request.POST.get(
                        "factor_desencadenante", ""
                    ),
                    "evolucion_problema": request.POST.get("evolucion_problema", ""),
                    # Higiene del sueño
                    "horario_acostarse": request.POST.get("horario_acostarse", ""),
                    "horario_levantarse": request.POST.get("horario_levantarse", ""),
                    "tiempo_dormirse": request.POST.get("tiempo_dormirse", ""),
                    "despertares_nocturnos": request.POST.get(
                        "despertares_nocturnos", ""
                    ),
                    "causa_despertares": request.POST.get("causa_despertares", ""),
                    "tiempo_volver_dormir": request.POST.get(
                        "tiempo_volver_dormir", ""
                    ),
                    "despertar_final": request.POST.get("despertar_final", ""),
                    "calidad_sueno": request.POST.get("calidad_sueno", ""),
                    # Ambiente de sueño
                    "habitacion_propia": request.POST.get("habitacion_propia") == "si",
                    "comparte_cama": request.POST.get("comparte_cama", ""),
                    "temperatura_habitacion": request.POST.get(
                        "temperatura_habitacion", ""
                    ),
                    "ruido_ambiente": request.POST.get("ruido_ambiente", ""),
                    "iluminacion": request.POST.get("iluminacion", ""),
                    # Hábitos pre-sueño
                    "actividades_antes_dormir": request.POST.get(
                        "actividades_antes_dormir", ""
                    ),
                    "uso_dispositivos": request.POST.get("uso_dispositivos") == "si",
                    "tiempo_dispositivos": request.POST.get("tiempo_dispositivos", ""),
                    "comida_antes_dormir": request.POST.get("comida_antes_dormir", ""),
                    "bebidas_antes_dormir": request.POST.get(
                        "bebidas_antes_dormir", ""
                    ),
                    # Síntomas diurnos
                    "somnolencia_diurna": request.POST.get("somnolencia_diurna", ""),
                    "fatiga": request.POST.get("fatiga", ""),
                    "dificultad_concentracion": request.POST.get(
                        "dificultad_concentracion", ""
                    ),
                    "cambios_humor": request.POST.get("cambios_humor", ""),
                    "microsuenos": request.POST.get("microsuenos") == "si",
                    # Síntomas nocturnos
                    "ronquidos": request.POST.get("ronquidos", ""),
                    "apneas_observadas": request.POST.get("apneas_observadas") == "si",
                    "movimientos_piernas": request.POST.get("movimientos_piernas")
                    == "si",
                    "parasomnia": request.POST.get("parasomnia", ""),
                    "sudoracion_nocturna": request.POST.get("sudoracion_nocturna")
                    == "si",
                    "nicturia": request.POST.get("nicturia", ""),
                    # Factores relacionados
                    "estres_actual": request.POST.get("estres_actual", ""),
                    "cambios_trabajo": request.POST.get("cambios_trabajo", ""),
                    "trabajo_turnos": request.POST.get("trabajo_turnos") == "si",
                    "tipo_turnos": request.POST.get("tipo_turnos", ""),
                    "viajes_frecuentes": request.POST.get("viajes_frecuentes") == "si",
                    # Tratamientos previos
                    "tratamientos_previos": request.POST.get(
                        "tratamientos_previos", ""
                    ),
                    "medicamentos_sueno": request.POST.get("medicamentos_sueno", ""),
                    "efectividad_tratamientos": request.POST.get(
                        "efectividad_tratamientos", ""
                    ),
                    # Impacto funcional
                    "impacto_trabajo": request.POST.get("impacto_trabajo", ""),
                    "impacto_social": request.POST.get("impacto_social", ""),
                    "impacto_familiar": request.POST.get("impacto_familiar", ""),
                    "escala_impacto": request.POST.get("escala_impacto", ""),
                    # Observaciones
                    "observaciones_adicionales": request.POST.get(
                        "observaciones_adicionales", ""
                    ),
                },
            )

            # Si no es nuevo, actualizar los campos
            if not created:
                # Motivo de consulta
                anamnesis.motivo_consulta = request.POST.get("motivo_consulta", "")
                anamnesis.enfermedad_actual = request.POST.get("enfermedad_actual", "")

                # Antecedentes del sueño
                anamnesis.inicio_problemas_sueno = request.POST.get(
                    "inicio_problemas_sueno", ""
                )
                anamnesis.factor_desencadenante = request.POST.get(
                    "factor_desencadenante", ""
                )
                anamnesis.evolucion_problema = request.POST.get(
                    "evolucion_problema", ""
                )

                # Higiene del sueño
                anamnesis.horario_acostarse = request.POST.get("horario_acostarse", "")
                anamnesis.horario_levantarse = request.POST.get(
                    "horario_levantarse", ""
                )
                anamnesis.tiempo_dormirse = request.POST.get("tiempo_dormirse", "")
                anamnesis.despertares_nocturnos = request.POST.get(
                    "despertares_nocturnos", ""
                )
                anamnesis.causa_despertares = request.POST.get("causa_despertares", "")
                anamnesis.tiempo_volver_dormir = request.POST.get(
                    "tiempo_volver_dormir", ""
                )
                anamnesis.despertar_final = request.POST.get("despertar_final", "")
                anamnesis.calidad_sueno = request.POST.get("calidad_sueno", "")

                # Ambiente de sueño
                anamnesis.habitacion_propia = (
                    request.POST.get("habitacion_propia") == "si"
                )
                anamnesis.comparte_cama = request.POST.get("comparte_cama", "")
                anamnesis.temperatura_habitacion = request.POST.get(
                    "temperatura_habitacion", ""
                )
                anamnesis.ruido_ambiente = request.POST.get("ruido_ambiente", "")
                anamnesis.iluminacion = request.POST.get("iluminacion", "")

                # Hábitos pre-sueño
                anamnesis.actividades_antes_dormir = request.POST.get(
                    "actividades_antes_dormir", ""
                )
                anamnesis.uso_dispositivos = (
                    request.POST.get("uso_dispositivos") == "si"
                )
                anamnesis.tiempo_dispositivos = request.POST.get(
                    "tiempo_dispositivos", ""
                )
                anamnesis.comida_antes_dormir = request.POST.get(
                    "comida_antes_dormir", ""
                )
                anamnesis.bebidas_antes_dormir = request.POST.get(
                    "bebidas_antes_dormir", ""
                )

                # Síntomas diurnos
                anamnesis.somnolencia_diurna = request.POST.get(
                    "somnolencia_diurna", ""
                )
                anamnesis.fatiga = request.POST.get("fatiga", "")
                anamnesis.dificultad_concentracion = request.POST.get(
                    "dificultad_concentracion", ""
                )
                anamnesis.cambios_humor = request.POST.get("cambios_humor", "")
                anamnesis.microsuenos = request.POST.get("microsuenos") == "si"

                # Síntomas nocturnos
                anamnesis.ronquidos = request.POST.get("ronquidos", "")
                anamnesis.apneas_observadas = (
                    request.POST.get("apneas_observadas") == "si"
                )
                anamnesis.movimientos_piernas = (
                    request.POST.get("movimientos_piernas") == "si"
                )
                anamnesis.parasomnia = request.POST.get("parasomnia", "")
                anamnesis.sudoracion_nocturna = (
                    request.POST.get("sudoracion_nocturna") == "si"
                )
                anamnesis.nicturia = request.POST.get("nicturia", "")

                # Factores relacionados
                anamnesis.estres_actual = request.POST.get("estres_actual", "")
                anamnesis.cambios_trabajo = request.POST.get("cambios_trabajo", "")
                anamnesis.trabajo_turnos = request.POST.get("trabajo_turnos") == "si"
                anamnesis.tipo_turnos = request.POST.get("tipo_turnos", "")
                anamnesis.viajes_frecuentes = (
                    request.POST.get("viajes_frecuentes") == "si"
                )

                # Tratamientos previos
                anamnesis.tratamientos_previos = request.POST.get(
                    "tratamientos_previos", ""
                )
                anamnesis.medicamentos_sueno = request.POST.get(
                    "medicamentos_sueno", ""
                )
                anamnesis.efectividad_tratamientos = request.POST.get(
                    "efectividad_tratamientos", ""
                )

                # Impacto funcional
                anamnesis.impacto_trabajo = request.POST.get("impacto_trabajo", "")
                anamnesis.impacto_social = request.POST.get("impacto_social", "")
                anamnesis.impacto_familiar = request.POST.get("impacto_familiar", "")
                anamnesis.escala_impacto = request.POST.get("escala_impacto", "")

                # Observaciones
                anamnesis.observaciones_adicionales = request.POST.get(
                    "observaciones_adicionales", ""
                )

                anamnesis.save()

            # Procesar las relaciones ManyToMany
            # Sustancias
            sustancias_ids = request.POST.getlist("sustancias")
            if sustancias_ids:
                anamnesis.sustancias.set(sustancias_ids)

            # Síntomas
            sintomas_ids = request.POST.getlist("sintomas")
            if sintomas_ids:
                anamnesis.sintomas.set(sintomas_ids)

            # Pantallas
            pantallas_ids = request.POST.getlist("pantallas")
            if pantallas_ids:
                anamnesis.pantallas.set(pantallas_ids)

            # Tipos de queja
            quejas_ids = request.POST.getlist("tipos_queja")
            if quejas_ids:
                anamnesis.tipos_queja.set(quejas_ids)

            # Medicamentos
            medicamentos_ids = request.POST.getlist("medicamentos")
            if medicamentos_ids:
                anamnesis.medicamentos.set(medicamentos_ids)

            # Síntomas diurnos
            sintomas_diurnos_ids = request.POST.getlist("sintomas_diurnos")
            if sintomas_diurnos_ids:
                anamnesis.sintomas_diurnos.set(sintomas_diurnos_ids)

            # Actividades en cama
            actividades_cama_ids = request.POST.getlist("actividades_cama")
            if actividades_cama_ids:
                anamnesis.actividades_cama.set(actividades_cama_ids)

            # Actividades físicas
            actividades_fisicas_ids = request.POST.getlist("actividades_fisicas")
            if actividades_fisicas_ids:
                anamnesis.actividades_fisicas.set(actividades_fisicas_ids)

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "Anamnesis de sueño guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            messages.error(request, f"Error al guardar la anamnesis: {str(e)}")
            return redirect("detalle_paciente", paciente_id=paciente_id or 1)

    else:
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
            import traceback

            traceback.print_exc()

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
            import traceback

            traceback.print_exc()

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
            import traceback

            traceback.print_exc()

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
            import traceback

            traceback.print_exc()

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
            import traceback

            traceback.print_exc()

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

            print(
                f"DEBUG: visita_id={visita_id}, examen_id={examen_id}, paciente_id={paciente_id}"
            )
            print("=== DEBUG: TODOS LOS CAMPOS POST ===")
            for key, value in request.POST.items():
                if not key.startswith("csrf"):
                    print(f"Campo: '{key}' = '{value}'")
            print("=== FIN DEBUG ===")

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
            print(f"ERROR en Pittsburgh: {str(e)}")
            import traceback

            traceback.print_exc()

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

            # Obtener los campos según los NOMBRES EXACTOS del modelo StopBangResult
            ronquidos_fuertes = request.POST.get("ronquidos_fuertes", "")  # S - Snoring
            cansancio_diurno = request.POST.get("cansancio_diurno", "")  # T - Tired
            apneas_observadas = request.POST.get(
                "apneas_observadas", ""
            )  # O - Observed
            presion_arterial = request.POST.get("presion_arterial", "")  # P - Pressure
            imc_alto = request.POST.get("imc_alto", "")  # B - BMI
            edad_mayor_50 = request.POST.get("edad_mayor_50", "")  # A - Age
            circunferencia_cuello = request.POST.get(
                "circunferencia_cuello", ""
            )  # N - Neck
            genero_masculino = request.POST.get("genero_masculino", "")  # G - Gender

           

            # Función para calcular puntuación STOP-BANG
            def calcular_puntuacion_stopbang(campos):
                """Calcula la puntuación del cuestionario STOP-BANG (0-8 puntos)"""
                puntuacion = 0

                # Cada "Sí" suma 1 punto
                if campos.get("ronquidos_fuertes", "").lower() in ["sí", "si", "yes"]:
                    puntuacion += 1
                if campos.get("cansancio_diurno", "").lower() in ["sí", "si", "yes"]:
                    puntuacion += 1
                if campos.get("apneas_observadas", "").lower() in ["sí", "si", "yes"]:
                    puntuacion += 1
                if campos.get("presion_arterial", "").lower() in ["sí", "si", "yes"]:
                    puntuacion += 1
                if campos.get("imc_alto", "").lower() in ["sí", "si", "yes"]:
                    puntuacion += 1
                if campos.get("edad_mayor_50", "").lower() in ["sí", "si", "yes"]:
                    puntuacion += 1
                if campos.get("circunferencia_cuello", "").lower() in [
                    "sí",
                    "si",
                    "yes",
                ]:
                    puntuacion += 1
                if campos.get("genero_masculino", "").lower() in ["sí", "si", "yes"]:
                    puntuacion += 1

                return puntuacion

            # Calcular puntuación automáticamente
            campos_stopbang = {
                "ronquidos_fuertes": ronquidos_fuertes,
                "cansancio_diurno": cansancio_diurno,
                "apneas_observadas": apneas_observadas,
                "presion_arterial": presion_arterial,
                "imc_alto": imc_alto,
                "edad_mayor_50": edad_mayor_50,
                "circunferencia_cuello": circunferencia_cuello,
                "genero_masculino": genero_masculino,
            }

            puntuacion_calculada = calcular_puntuacion_stopbang(campos_stopbang)
            puntuacion_form = request.POST.get(
                "puntuacion_total", str(puntuacion_calculada)
            )

            try:
                puntuacion_total = (
                    int(puntuacion_form)
                    if puntuacion_form.isdigit()
                    else puntuacion_calculada
                )
            except:
                puntuacion_total = puntuacion_calculada


            # Determinar interpretación según puntuación STOP-BANG
            if puntuacion_total <= 2:
                interpretacion = "Bajo riesgo de apnea del sueño"
                categoria_riesgo = "Bajo"
            elif puntuacion_total <= 4:
                interpretacion = "Riesgo intermedio de apnea del sueño"
                categoria_riesgo = "Intermedio"
            else:
                interpretacion = "Alto riesgo de apnea del sueño"
                categoria_riesgo = "Alto"

            # Crear o actualizar el resultado STOP-BANG usando los CAMPOS EXACTOS del modelo
            stopbang_result, created = StopBangResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    # Campos exactos según tu modelo StopBangResult
                    "ronquidos_fuertes": ronquidos_fuertes,
                    "cansancio_diurno": cansancio_diurno,
                    "apneas_observadas": apneas_observadas,
                    "presion_arterial": presion_arterial,
                    "imc_alto": imc_alto,
                    "edad_mayor_50": edad_mayor_50,
                    "circunferencia_cuello": circunferencia_cuello,
                    "genero_masculino": genero_masculino,
                    "puntuacion_total": puntuacion_total,
                    "interpretacion": interpretacion,
                },
            )

            print(
                f"DEBUG: STOP-BANG {'creado' if created else 'actualizado'} con ID: {stopbang_result.id}"
            )
            print(
                f"DEBUG: Verificación - ronquidos_fuertes: {stopbang_result.ronquidos_fuertes}"
            )
            print(
                f"DEBUG: Verificación - puntuacion_total: {stopbang_result.puntuacion_total}"
            )
            print(
                f"DEBUG: Verificación - interpretacion: {stopbang_result.interpretacion}"
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                f"✅ Cuestionario STOP-BANG guardado exitosamente.\n"
                f"📊 Puntuación: {puntuacion_total}/8 - {categoria_riesgo} riesgo\n"
                f"🔍 Interpretación: {interpretacion}",
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
           
            import traceback

            traceback.print_exc()

            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
                    print("DEBUG: Estado revertido a pendiente")
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
            import traceback

            traceback.print_exc()

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

            messages.success(request, "✅ Escala de Lawton y Brody guardada exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar el examen Lawton y Brody: {str(e)}")
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
                "satisfaccion_vida", "disminuir_actividades", "vida_vacia", "aburrido_frecuente",
                "buen_animo", "preocupacion", "felicidad", "frecuencia_desamparado",
                "quedarse_casa", "problemas_memoria", "maravilla_vivir", "inutil",
                "lleno_energia", "sin_esperanza", "otras_personas_mejor"
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
                request, "✅ Escala de Depresión Geriátrica de Yesavage guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

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

            pide_ayuda= request.POST.get("pide_ayuda_texto")
            falta_tiempo_propio= request.POST.get("falta_tiempo_propio_texto")
            agobio= request.POST.get("agobio_texto")
            verguenza_conducta= request.POST.get("verguenza_conducta_texto")
            sentir_enfado= request.POST.get("sentir_enfado_texto")
            afectar_relacion_negativamente= request.POST.get("afectar_relacion_negativamente_texto")
            miedo_futuro= request.POST.get("miedo_futuro_texto")
            dependencia= request.POST.get("dependencia_texto")
            sentir_tension= request.POST.get("sentir_tension_texto")
            deterioro_salud= request.POST.get("deterioro_salud_texto")
            menos_intimidad= request.POST.get("menos_intimidad_texto")
            resentir_vida_social= request.POST.get("resentir_vida_social_texto")
            desatender_amistades= request.POST.get("desatender_amistades_texto")
            unica_dependencia= request.POST.get("unica_dependencia_texto")
            dinero_insuficiente= request.POST.get("dinero_insuficiente_texto")
            incapaz_mas_tiempo= request.POST.get("incapaz_mas_tiempo_texto")
            perder_control_vida= request.POST.get("perder_control_vida_texto")
            cuidado_a_otros= request.POST.get("cuidado_a_otros_texto")
            indecision_que_hacer= request.POST.get("indecision_que_hacer_texto")
            hacer_mas= request.POST.get("hacer_mas_texto")
            cuidar_mejor= request.POST.get("cuidar_mejor_texto")
            grado_carga= request.POST.get("grado_carga_texto")

            puntaje_total = request.POST.get("puntaje_total")
            interpretacion = request.POST.get("interpretacion")

            zarit, created = ZaritResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults={
                    "pide_ayuda":pide_ayuda,
                    "falta_tiempo_propio":falta_tiempo_propio,
                    "agobio":agobio,
                    "verguenza_conducta":verguenza_conducta,
                    "sentir_enfado":sentir_enfado,
                    "afectar_relacion_negativamente":afectar_relacion_negativamente,
                    "miedo_futuro":miedo_futuro,
                    "dependencia":dependencia,
                    "sentir_tension":sentir_tension,
                    "deterioro_salud":deterioro_salud,
                    "menos_intimidad":menos_intimidad,
                    "resentir_vida_social":resentir_vida_social,
                    "desatender_amistades":desatender_amistades,
                    "unica_dependencia":unica_dependencia,
                    "dinero_insuficiente":dinero_insuficiente,
                    "incapaz_mas_tiempo":incapaz_mas_tiempo,
                    "perder_control_vida":perder_control_vida,
                    "cuidado_a_otros":cuidado_a_otros,
                    "indecision_que_hacer":indecision_que_hacer,
                    "hacer_mas":hacer_mas,
                    "cuidar_mejor":cuidar_mejor,
                    "grado_carga":grado_carga,
                    "puntaje_total": puntaje_total,
                    "interpretacion": interpretacion,
                },
            )

            # Marcar como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                "✅ Escala de Zarit guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

            # Revertir estado si falla
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar la escala de Zarit: {str(e)}"
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
                request, "✅ Autovaloración del Estado de Salud (EVA EuroQol) guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la Autovaloración del Estado de Salud (EVA EuroQol): {str(e)}"
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
                "ideas_delirantes", "alucinaciones", "agitacion", "depresion",
                "ansiedad", "euforia", "apatia", "desinhibicion",
                "irritabilidad", "conducta_motor", "sueno", "apetito"
            ]

            data = {}
            for item in items:
                data[item] = request.POST.get(item)
                data[f"{item}_frecuencia"] = request.POST.get(f"{item}_frecuencia_texto")
                data[f"{item}_gravedad"] = request.POST.get(f"{item}_gravedad_texto")
                data[f"{item}_F_G"] = request.POST.get(f"{item}_resultado")
                data[f"{item}_distres"] = request.POST.get(f"{item}_distres_texto")

            # Crear o actualizar el resultado del NPI
            npi, created = CuidadorNPIResult.objects.update_or_create(
                visita_examen=visita_examen,
                defaults=data
            )

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(request, "✅ Inventario Neuropsiquiátrico (NPI) guardado exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar el Inventario Neuropsiquiátrico (NPI): {str(e)}"
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
                "recordar_fecha", "orientacion_lugares_nuevos", "recordar_llamadas",
                "entender_conversacion", "firmar", "entender_lectura", "mantener_orden",
                "recordar_lugar_objetos", "escribir", "manejar_dinero",
                "orientacion_zona_donde_vive", "recordar_citas", "pasatiempos",
                "comunicarse_con_gente", "calculos_mentales", "recordar_compras",
                "contener_orina", "entender_pelicula", "orientacion_en_casa",
                "hacer_tareas_hogar", "comer_solo", "realizar_tramites",
                "decisiones_y_adaptacion", "egoismo", "enojo_menos_paciencia",
                "llorar_con_facilidad", "reir_situaciones_inapropiadas", "temas_sexuales",
                "falta_de_interes", "deprimido"
            ]

            # Extraer respuestas
            respuestas = {campo: request.POST.get(campo+"_texto") for campo in campos}

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
                f"✅ Escala AQ-D Cuidador guardada correctamente. Puntaje total: {puntaje_total}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar la escala AQ-D Cuidador: {str(e)}"
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
                "recordar_fecha", "orientacion_lugares_nuevos", "recordar_llamadas",
                "entender_conversacion", "firmar", "entender_lectura", "mantener_orden",
                "recordar_lugar_objetos", "escribir", "manejar_dinero",
                "orientacion_zona_donde_vive", "recordar_citas", "pasatiempos",
                "comunicarse_con_gente", "calculos_mentales", "recordar_compras",
                "contener_orina", "entender_pelicula", "orientacion_en_casa",
                "hacer_tareas_hogar", "comer_solo", "realizar_tramites",
                "decisiones_y_adaptacion", "egoismo", "enojo_menos_paciencia",
                "llorar_con_facilidad", "reir_situaciones_inapropiadas", "temas_sexuales",
                "falta_de_interes", "deprimido"
            ]

            # Extraer respuestas
            respuestas = {campo: request.POST.get(campo+"_texto") for campo in campos}

            # Calcular puntaje total
            puntaje_total = 0
            for campo in campos:
                try:
                    valor = int(request.POST.get(campo, 0))
                    puntaje_total += valor
                except ValueError:
                    pass

            # Guardar en BD (update si ya existe)
            aqdparticipante, created =AQDParticipanteResult.objects.update_or_create(
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
                f"✅ Escala AQ-D Participante guardada exitosamente. Puntaje total: {puntaje_total}"
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

            # Revertir estado si falla
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(
                request,
                f"❌ Error al guardar la escala AQ-D Participante: {str(e)}"
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
                if hasattr(field, "get_internal_type") and field.get_internal_type() == "BooleanField":
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

            messages.success(request, "✅ Cuestionario CDR - Participante guardado exitosamente.")
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass

            messages.error(request, f"❌ Error al guardar el cuestionario CDR - Participante: {str(e)}")
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
            educacion_baja = True if request.POST.get("educacion_baja") == "on" else False

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

            print(
                f"DEBUG: MoCA {'creado' if created else 'actualizado'} con ID: {moca.id}"
            )
            print(f"DEBUG: Puntaje total: {moca.puntaje_total}")
            print(f"DEBUG: Interpretación: {moca.interpretacion}")

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
            import traceback

            traceback.print_exc()

            # Revertir estado si hubo error
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
                    print("DEBUG: Estado revertido a pendiente")
            except:
                pass

            messages.error(
                request, f"❌ Error al guardar la escala MoCA: {str(e)}"
            )
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
                "evento_recuerda_semana": request.POST.get("evento_recuerda_semana", ""),
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
                "memoria_causa_jubilacion": request.POST.get("memoria_causa_jubilacion", ""),
                "dificultades_trabajo_memoria": request.POST.get("dificultades_trabajo_memoria", ""),
                "condujo_alguna_vez": request.POST.get("condujo_alguna_vez", ""),
                "conduce_actualmente": request.POST.get("conduce_actualmente", ""),
                "dejo_de_conducir_por_memoria": request.POST.get("dejo_de_conducir_por_memoria", ""),
                "riesgos_conduccion": request.POST.get("riesgos_conduccion", ""),
                "compras_independientes": request.POST.get("compras_independientes", ""),
                "actividades_fuera_hogar": request.POST.get("actividades_fuera_hogar", ""),
                "asiste_funciones_sociales": request.POST.get("asiste_funciones_sociales", ""),
                "motivo_no_funciones": request.POST.get("motivo_no_funciones", ""),
                "parece_enfermo": request.POST.get("parece_enfermo", ""),
                "participa_hogar_geriatrico": request.POST.get("participa_hogar_geriatrico", ""),
                "info_suficiente_comunitarias": request.POST.get("info_suficiente_comunitarias", ""),
                "notas_comunitarias": request.POST.get("notas_comunitarias", ""),
                "cambios_tareas_domesticas": request.POST.get("cambios_tareas_domesticas", ""),
                "cosas_que_aun_realiza_domesticas": request.POST.get("cosas_que_aun_realiza_domesticas", ""),
                "cambios_pasatiempos": request.POST.get("cambios_pasatiempos", ""),
                "cosas_que_aun_realiza_pasatiempos": request.POST.get("cosas_que_aun_realiza_pasatiempos", ""),
                "actividades_no_realiza_en_hogar": request.POST.get("actividades_no_realiza_en_hogar", ""),
                "habilidad_domestica_dementia_scale": request.POST.get("habilidad_domestica_dementia_scale") or None,
                "descripcion_habilidad_domestica": request.POST.get("descripcion_habilidad_domestica", ""),
                "nivel_desempeno_domestico": request.POST.get("nivel_desempeno_domestico", ""),
                "notas_domesticas_pasatiempos": request.POST.get("notas_domesticas_pasatiempos", ""),
                "cuidado_p1": request.POST.get("cuidado_p1") or None,
                "cuidado_p2": request.POST.get("cuidado_p2") or None,
                "cuidado_p3": request.POST.get("cuidado_p3") or None,
                "cuidado_p4": request.POST.get("cuidado_p4") or None,
            }

            # Guardar o actualizar
            cdrcuidador, created = CDRCuidadorResult.objects.update_or_create(
                visita_examen=visita_examen, defaults=campos
            )

            print(f"DEBUG: CDR Cuidador {'creado' if created else 'actualizado'} con ID {cdrcuidador.id}")

            # Marcar examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request,
                "✅ Escala CDR (Cuidador) guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                if "visita_examen" in locals():
                    visita_examen.estado = "pendiente"
                    visita_examen.save()
            except:
                pass
            messages.error(
                request,
                f"❌ Error al guardar el cuestionario CDR (Cuidador): {str(e)}"
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
            campos = {k: request.POST.get(k+"_texto", "") for k in [
                # Autocuidado
                "comer","vestirse","banarse","bano","medicamentos","apariencia",
                
                # Cuidado del hogar
                "cocinar","poner_mesa","aseo_hogar","mantener_casa","reparar_hogar","lavado_ropa",
                
                # Trabajo y recreación
                "trabajo","recreacion","organizaciones","desplazamiento",
                
                # Compras y dinero
                "alimentos","dinero_efectivo","finanzas",
                
                # Viajes
                "transporte_publico","manejo_vehiculos","movilidad_barrio","viajes_fuera",
                
                # Comunicación
                "telefono","conversacion","comprension","lectura","escritura",
            
                # Tecnología
                "computador","telefono_celular","cajero","internet","email","redes_sociales",
            ]}

            # Recoger los puntajes de cada sección
            puntajes = {
                "puntaje_autocuidado": request.POST.get("puntaje_autocuidado"),
                "puntaje_cuidado_hogar": request.POST.get("puntaje_cuidado_hogar"),
                "puntaje_trabajo_recreacion": request.POST.get("puntaje_trabajo_recreacion"),
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
                defaults=defaults
            )

            print(f"DEBUG: RedLatSpanish {'creado' if created else 'actualizado'} con ID {redlatspanish.id}")

            # Marcar el examen como completado
            visita_examen.estado = "completado"
            visita_examen.fecha_completado = timezone.now()
            visita_examen.save()

            messages.success(
                request, "✅ Evaluación RedLat Spanish guardada exitosamente."
            )
            return redirect("detalle_paciente", paciente_id=paciente_id)

        except Exception as e:
            import traceback
            traceback.print_exc()

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
