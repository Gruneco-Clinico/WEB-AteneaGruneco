# -*- encoding: utf-8 -*-
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse, HttpResponseServerError
from django.template import loader
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.forms.models import model_to_dict
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from django.core.mail import send_mail, EmailMessage
from django.db.models import Max
from datetime import datetime, timedelta
from ..models import *
from ..forms import ProyectoForm, RegistroDemograficoForm
import json
import requests
import logging
import os
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
from .auth import is_superuser

logger = logging.getLogger(__name__)

@login_required
def lista_pacientes(request):
    pacientes = DatosDemograficos.objects.all()
    proyectos = Proyecto.objects.all()
    filtro_proyecto = request.GET.get("proyecto", "")
    if filtro_proyecto:
        try:
            pacientes = pacientes.filter(proyectos__id=int(filtro_proyecto))
        except (ValueError, TypeError):
            pass
    return render(
        request,
        "home/tables.html",
        {
            "pacientes": pacientes,
            "proyectos": proyectos,
            "filtro_proyecto": filtro_proyecto,
        },
    )


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
@user_passes_test(is_superuser, login_url="/login/")
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

        codigo = proyecto.codigo_siu
        # Prefijo: SUE, ANG, etc.
        prefijo = codigo.upper()

        # Obtener último código del proyecto
        ultimo = ProyectoPacienteExtra.objects.filter(proyecto=proyecto).aggregate(
            Max("codigo_proyecto")
        )["codigo_proyecto__max"]

        if ultimo:
            # Extrae el número: SUE_0003 -> 3
            consecutivo = int(ultimo.split("_")[-1]) + 1
        else:
            consecutivo = 1

        codigo_final = f"{prefijo}_{consecutivo:04d}"

        ProyectoPacienteExtra.objects.create(
            proyecto=proyecto, paciente=paciente, codigo_proyecto=codigo_final
        )

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


@login_required
@user_passes_test(is_superuser, login_url="/login/")
def quitar_paciente_proyecto(request, paciente_id, proyecto_id):
    """
    Quita la relación M2M entre paciente y proyecto.
    NO elimina el paciente del sistema, solo la asociación.
    También elimina el ProyectoPacienteExtra correspondiente.
    """
    if request.method == "POST":
        paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
        proyecto = get_object_or_404(Proyecto, id=proyecto_id)

        # Quitar relación M2M
        proyecto.pacientes.remove(paciente)

        # Eliminar registro extra de código de proyecto
        ProyectoPacienteExtra.objects.filter(
            proyecto=proyecto, paciente=paciente
        ).delete()

        messages.success(
            request,
            f"El paciente ha sido removido del proyecto '{proyecto.nombre}'."
        )
    else:
        messages.error(request, "Método no permitido.")

    return redirect("detalle_paciente", paciente_id=paciente_id)


#######################################################
# registro externo datos demograficos


def formulario_demografico_externo(request):
    """Permite el registro de datos demográficos desde enlace público"""
    if request.method == "POST":
        try:
            # Validar campos obligatorios
            campos_requeridos = [
                "primer_nombre",
                "primer_apellido",
                "numero_documento",
                "fecha_nacimiento",
                "edad",
                "correo",
                "celular",
                "tipo_documento",
            ]

            for campo in campos_requeridos:
                if not request.POST.get(campo):
                    raise ValueError(
                        f"El campo {campo.replace('_', ' ')} es obligatorio"
                    )

            # Verificar si ya existe un paciente con el mismo documento
            if DatosDemograficos.objects.filter(
                numero_documento=request.POST["numero_documento"]
            ).exists():
                messages.warning(
                    request, "Ya existe un registro con este número de documento."
                )
                return render(request, "info_paciente/formulario_externo.html")

            # Crear registro
            paciente_nuevo = DatosDemograficos(
                primer_nombre=request.POST["primer_nombre"].strip(),
                primer_apellido=request.POST["primer_apellido"].strip(),
                numero_documento=request.POST["numero_documento"].strip(),
                fecha_nacimiento=request.POST["fecha_nacimiento"],
                edad=request.POST["edad"],
                correo=request.POST["correo"].strip().lower(),
                celular=request.POST["celular"].strip(),
                regimen=request.POST.get("regimen", "Contributivo"),
                tipo_documento=request.POST["tipo_documento"],
                # Campos opcionales
                segundo_nombre=request.POST.get("segundo_nombre", "").strip(),
                segundo_apellido=request.POST.get("segundo_apellido", "").strip(),
                genero=request.POST.get("genero", ""),
                escolaridad=request.POST.get("escolaridad", ""),
                lateralidad=request.POST.get("lateralidad", ""),
                estado_civil=request.POST.get("estado_civil", ""),
                ocupacion=request.POST.get("ocupacion", "").strip(),
                eps=request.POST.get("eps", "").strip(),
                direccion=request.POST.get("direccion", "").strip(),
                municipio_residencia=request.POST.get(
                    "municipio_residencia", ""
                ).strip(),
                departamento_residencia=request.POST.get(
                    "departamento_residencia", ""
                ).strip(),
                pais_residencia=request.POST.get("pais_residencia", "Colombia"),
                municipio_nacimiento=request.POST.get(
                    "municipio_nacimiento", ""
                ).strip(),
                departamento_nacimiento=request.POST.get(
                    "departamento_nacimiento", ""
                ).strip(),
                pais_nacimiento=request.POST.get("pais_nacimiento", "Colombia"),
                grupo_sanguineo=request.POST.get("grupo_sanguineo", ""),
                religion=request.POST.get("religion", "").strip(),
            )

            paciente_nuevo.save()

            # ===== NUEVA FUNCIONALIDAD: VINCULAR AL PROYECTO ID 8 =====
            try:
                proyecto_automatico = Proyecto.objects.get(id=8)
                proyecto_automatico.pacientes.add(paciente_nuevo)
                proyecto_automatico.save()

            except Proyecto.DoesNotExist:
                print(
                    f"⚠️ El proyecto con ID 8 no existe. Paciente {paciente_nuevo.id} registrado sin vinculación automática."
                )
            except Exception as e:
                print(
                    f"❌ Error al vincular paciente {paciente_nuevo.id} al proyecto ID 8: {str(e)}"
                )

            # ===== NUEVA FUNCIONALIDAD: CREAR VISITA AUTOMÁTICA =====
            try:
                tipo_visita_automatico = TipoVisita.objects.get(id=7)

                # Crear visita automática
                visita_automatica = Visita.objects.create(
                    paciente=paciente_nuevo,
                    nombre="VISITA EPWORTH/MEW",
                    Tipo_visita=tipo_visita_automatico,
                    fecha=timezone.now().date(),
                )

                # Crear los exámenes asociados automáticamente según el tipo de visita
                if (
                    hasattr(tipo_visita_automatico, "examenes")
                    and tipo_visita_automatico.examenes
                ):
                    examenes_tipo_visita = tipo_visita_automatico.examenes

                    for examen_data in examenes_tipo_visita:
                        try:
                            examen = Examen.objects.get(id=examen_data["id"])
                            VisitaExamen.objects.create(
                                visita=visita_automatica,
                                examen=examen,
                                estado="pendiente",
                            )

                        except Examen.DoesNotExist:
                            print(f"⚠️ Examen con ID {examen_data['id']} no existe")
                        except Exception as e:
                            print(
                                f"❌ Error al asociar examen {examen_data['id']}: {str(e)}"
                            )

            except TipoVisita.DoesNotExist:
                print(
                    f"⚠️ El tipo de visita con ID 7 no existe. No se creó visita automática para el paciente {paciente_nuevo.id}."
                )
            except Exception as e:
                print(
                    f"❌ Error al crear visita automática para el paciente {paciente_nuevo.id}: {str(e)}"
                )
            # ===== FIN NUEVA FUNCIONALIDAD =====

            # Generar código de confirmación único
            from datetime import datetime

            codigo_confirmacion = (
                f"ATG-{paciente_nuevo.id:05d}-{datetime.now().strftime('%Y%m')}"
            )

            # Almacenar datos para la confirmación
            request.session["registro_completado"] = {
                "codigo": codigo_confirmacion,
                "nombre": f"{paciente_nuevo.primer_nombre} {paciente_nuevo.primer_apellido}",
                "documento": paciente_nuevo.numero_documento,
                "correo": paciente_nuevo.correo,
                "paciente_id": paciente_nuevo.id,
            }

            return redirect("confirmacion_registro_externo")

        except ValueError as ve:
            messages.error(request, str(ve))
        except Exception as e:
            messages.error(
                request, f"Ocurrió un error al procesar su registro: {str(e)}"
            )

        return render(request, "registro_publico/sleepFormRegister.html")

    # Método GET - mostrar formulario
    return render(request, "registro_publico/sleepFormRegister.html")


def consulta_examenes(request):
    documento = request.GET.get("documento", "").strip()

    # Validate input — reject empty or too-short document numbers
    if not documento or len(documento) < 5:
        return JsonResponse({"examenes": []})

    # 1. Verificar si existe un paciente con ese documento
    paciente = DatosDemograficos.objects.filter(numero_documento=documento).first()

    if not paciente:
        # Return same shape as "no exams" — prevents patient enumeration
        return JsonResponse({"examenes": []})

    # 2. Buscar su visita más reciente
    visita = Visita.objects.filter(paciente=paciente).order_by("-id").first()

    if not visita:
        return JsonResponse({"examenes": []})

    # 3. Buscar exámenes pendientes Y exámenes en proceso
    examenes = VisitaExamen.objects.filter(
        visita=visita, estado__in=["pendiente", "en_progreso"]
    )

    examenes_data = []

    for ve in examenes:
        # Detectar el estado para enviarlo al frontend
        estado = ve.estado  # pendiente | en_proceso

        # ======================
        # EPWORTH (id = 14)
        # ======================
        if ve.examen_id == 14:
            examenes_data.append(
                {
                    "nombre": ve.examen.nombre,
                    "estado": estado,
                    "url": f"/guardar-examen-publico-epworth/?paciente_id={paciente.id}",
                }
            )
            continue

        # ======================
        # MEW (id = 16)
        # ======================
        if ve.examen_id == 16:
            examenes_data.append(
                {
                    "nombre": ve.examen.nombre,
                    "estado": estado,
                    "url": f"/guardar-examen-publico-mew/?paciente_id={paciente.id}",
                }
            )
            continue

        # ======================
        # PITTSBURGH (id = 13)
        # ======================
        if ve.examen_id == 13:
            examenes_data.append(
                {
                    "nombre": ve.examen.nombre,
                    "estado": estado,
                    "url": f"/guardar-examen-publico-pitsburg/?paciente_id={paciente.id}",
                }
            )
            continue

        # ======================
        # OTROS
        # ======================
        examenes_data.append(
            {
                "nombre": ve.examen.nombre,
                "estado": estado,
                "url": f"/examen/{ve.id}/",
            }
        )

    return JsonResponse({"examenes": examenes_data})


# ===== EXÁMENES PÚBLICOS =====


