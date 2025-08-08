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
        print("aqui")
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
                print(
                    f"Exámenes seleccionados para la visita {nueva_visita.id}: {lista_ids_examenes}"
                )

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
                print(
                    f"Error al decodificar JSON de exámenes: {examenes_seleccionados}"
                )
                print(f"Error específico: {str(e)}")
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
    print(examenes_tipo_visita)
    examenes_actuales = VisitaExamen.objects.filter(visita=visita).values_list(
        "examen_id", flat=True
    )
    print(examenes_actuales)
    # Exámenes ya asociados
    print("aqui")
    examenes_disponibles = Examen.objects.filter(id__in=examenes_tipo_visita).exclude(
        id__in=examenes_actuales
    )
    print(examenes_disponibles)
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
        if examenes_seleccionados:
            print(
                f"Exámenes seleccionados para actualizar en la visita {visita.id}: {examenes_seleccionados}"
            )

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
            "model": None,
        },  # CORREGIDO: Este es Pittsburgh
        14: {"template": "examenes_sueno/sueno_Epworth.html", "model": EpworthResult},
        15: {
            "template": "examenes_sueno/sueno_Stop_Bang.html",
            "model": StopBangResult,
        },
        16: {"template": "examenes_sueno/sueno_MEW.html", "model": MEWResult},
        17: {"template": "examenes_sueno/sueno_Berlín.html", "model": BerlinResult},
        18: {"template": "examenes_sueno/sueno_atenas.html", "model": AtenasResult},
        19: {"template": "examenes_sueno/sueno_ISI.html", "model": ISIResult},
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
                print(f"Datos encontrados para edición: {datos_examen}")

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
            print(f"ERROR: {str(e)}")
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
            print(f"ERROR en anamnesis: {str(e)}")
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

            print(
                f"DEBUG: visita_id={visita_id}, examen_id={examen_id}, paciente_id={paciente_id}"
            )

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
            print(f"ERROR en Atenas: {str(e)}")
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
