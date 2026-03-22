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
from django.urls import reverse
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
from ..tokens import generar_token_paciente, generar_token_consentimiento_envio, validar_token_consentimiento_envio

logger = logging.getLogger(__name__)


def _obtener_ip_cliente(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _normalizar_tipo_documento(tipo_documento):
    valores_permitidos = {"CC", "TI", "NUIP", "CE", "PS"}
    if tipo_documento in valores_permitidos:
        return tipo_documento
    return "CC"


def _build_codigos_map(pacientes_qs):
    """Return {paciente_id: [code1, code2, ...]} from ProyectoPacienteExtra."""
    from ..models import ProyectoPacienteExtra

    pac_ids = list(pacientes_qs.values_list("id", flat=True))
    ppe_qs = (
        ProyectoPacienteExtra.objects
        .filter(paciente_id__in=pac_ids)
        .select_related("proyecto")
        .order_by("proyecto__nombre")
    )
    codigos = {}
    for ppe in ppe_qs:
        codigos.setdefault(ppe.paciente_id, []).append(ppe.codigo_proyecto)
    return codigos


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
    codigos_map = _build_codigos_map(pacientes)
    # Attach codes to each patient object for easy template access
    for pac in pacientes:
        pac.codigos_list = codigos_map.get(pac.id, [])
    return render(
        request,
        "home/tables.html",
        {
            "pacientes": pacientes,
            "proyectos": proyectos,
            "filtro_proyecto": filtro_proyecto,
            "codigos_map": codigos_map,
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
    proyectos_con_consentimiento_firmado = list(
        ConsentimientoFirmaEnvio.objects.filter(
            paciente=paciente,
            estado="completado",
        ).values_list("proyecto_id", flat=True).distinct()
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
            "proyectos_con_consentimiento_firmado": proyectos_con_consentimiento_firmado,
        },
    )


@login_required
def enviar_link_firma_consentimiento(request, paciente_id, proyecto_id):
    if request.method != "POST":
        messages.error(request, "Metodo no permitido para enviar enlace.")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    paciente = get_object_or_404(DatosDemograficos, id=paciente_id)
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)

    if not proyecto.pacientes.filter(id=paciente.id).exists():
        messages.error(request, "El paciente no pertenece al proyecto seleccionado.")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    if not paciente.correo:
        messages.error(request, "El paciente no tiene correo registrado para enviar el enlace.")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    ya_firmado = ConsentimientoFirmaEnvio.objects.filter(
        paciente=paciente,
        proyecto=proyecto,
        estado="completado",
    ).exists()
    if ya_firmado:
        messages.info(request, "El consentimiento ya fue firmado para este proyecto.")
        return redirect("detalle_paciente", paciente_id=paciente_id)

    try:
        nombre_completo = " ".join(
            x
            for x in [
                paciente.primer_nombre,
                paciente.segundo_nombre,
                paciente.primer_apellido,
                paciente.segundo_apellido,
            ]
            if x
        ).strip()

        envio = ConsentimientoFirmaEnvio.objects.create(
            paciente=paciente,
            proyecto=proyecto,
            enviado_por=request.user,
            nombres_apellidos=nombre_completo,
            tipo_documento=_normalizar_tipo_documento(paciente.tipo_documento),
            numero_documento=paciente.numero_documento or "",
            correo_electronico=paciente.correo or "",
            celular=paciente.celular or "",
        )

        token = generar_token_consentimiento_envio(envio.id)
        enlace_relativo = reverse("firma_consentimiento_publico")
        enlace_publico = f"{request.build_absolute_uri(enlace_relativo)}?token={token}"

        mensaje = (
            f"Hola {nombre_completo or 'participante'},\n\n"
            f"Te compartimos el enlace para diligenciar la firma del consentimiento informado del proyecto: {proyecto.nombre}.\n\n"
            f"Enlace seguro:\n{enlace_publico}\n\n"
            "Este enlace tiene vencimiento por seguridad.\n\n"
            "Equipo ATENEA - GRUNECO"
        )

        send_mail(
            subject=f"Firma de consentimiento informado - {proyecto.nombre}",
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[paciente.correo],
            fail_silently=False,
        )

        messages.success(request, "Enlace de firma enviado correctamente al correo del paciente.")
    except Exception as e:
        logger.exception("Error enviando enlace de firma de consentimiento")
        messages.error(request, f"No se pudo enviar el enlace: {str(e)}")

    return redirect("detalle_paciente", paciente_id=paciente_id)


def firma_consentimiento_publico(request):
    token = request.GET.get("token") if request.method == "GET" else request.POST.get("token")
    envio_id = validar_token_consentimiento_envio(token)

    if envio_id is None:
        messages.error(request, "Enlace invalido o expirado. Solicite uno nuevo.")
        return redirect("formulario_demografico_externo")

    envio = get_object_or_404(
        ConsentimientoFirmaEnvio.objects.select_related("paciente", "proyecto"),
        id=envio_id,
    )

    if envio.estado == "completado":
        return render(
            request,
            "registro_publico/firma_consentimiento_exitoso.html",
            {"envio": envio},
        )

    if request.method == "POST":
        acepta_participacion = request.POST.get("acepta_participacion")
        acepta_uso = request.POST.get("acepta_uso_futuras_investigaciones")
        acepta_contacto = request.POST.get("acepta_contacto_nuevas_investigaciones")

        if not all([acepta_participacion, acepta_uso, acepta_contacto]):
            messages.error(request, "Debe responder todas las preguntas de aceptacion.")
            return render(
                request,
                "registro_publico/firma_consentimiento_publico.html",
                {"envio": envio, "token": token},
            )

        firma = request.POST.get("firma_participante", "").strip()
        if not firma:
            messages.error(request, "La firma es obligatoria.")
            return render(
                request,
                "registro_publico/firma_consentimiento_publico.html",
                {"envio": envio, "token": token},
            )

        envio.acepta_participacion = acepta_participacion == "si"
        envio.acepta_uso_futuras_investigaciones = acepta_uso == "si"
        envio.acepta_contacto_nuevas_investigaciones = acepta_contacto == "si"
        envio.nombres_apellidos = request.POST.get("nombres_apellidos", "").strip()
        envio.tipo_documento = _normalizar_tipo_documento(request.POST.get("tipo_documento"))
        envio.numero_documento = request.POST.get("numero_documento", "").strip()
        envio.fecha_firma = request.POST.get("fecha_firma") or None
        envio.hora_firma = request.POST.get("hora_firma") or None
        envio.correo_electronico = request.POST.get("correo_electronico", "").strip()
        envio.celular = request.POST.get("celular", "").strip()
        envio.firma_participante = firma
        envio.fecha_guardado_formulario = timezone.now()
        envio.ip_guardado_formulario = _obtener_ip_cliente(request)
        envio.estado = "completado"
        envio.save()

        return render(
            request,
            "registro_publico/firma_consentimiento_exitoso.html",
            {"envio": envio},
        )

    return render(
        request,
        "registro_publico/firma_consentimiento_publico.html",
        {"envio": envio, "token": token},
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

            # ===== VINCULAR PROYECTO: Caracterización sueño =====
            proyecto_vinculado = None

            try:
                proyecto_vinculado = Proyecto.objects.get(id=11)  # ID fijo para "Caracterización sueño"
                proyecto_vinculado.pacientes.add(paciente_nuevo)

                # Generar código de proyecto (ej: CRS_0001)
                prefijo = (proyecto_vinculado.codigo_siu or "").upper()
                ultimo = ProyectoPacienteExtra.objects.filter(
                    proyecto=proyecto_vinculado
                ).aggregate(Max("codigo_proyecto"))["codigo_proyecto__max"]

                if ultimo:
                    consecutivo = int(ultimo.split("_")[-1]) + 1
                else:
                    consecutivo = 1

                codigo_final = f"{prefijo}_{consecutivo:04d}"
                ProyectoPacienteExtra.objects.create(
                    proyecto=proyecto_vinculado,
                    paciente=paciente_nuevo,
                    codigo_proyecto=codigo_final,
                )

                logger.info(
                    "Paciente %s vinculado al proyecto '%s' con código %s",
                    paciente_nuevo.id,
                    proyecto_vinculado.nombre,
                    codigo_final,
                )
            except Proyecto.DoesNotExist:
                logger.error(
                    "Proyecto 'Caracterización sueño' no existe. Paciente %s no fue vinculado a ningún proyecto.",
                    paciente_nuevo.id,
                )
            except Exception as e:
                logger.error(
                    "Error al vincular paciente %s al proyecto 'Caracterización sueño': %s",
                    paciente_nuevo.id,
                    e,
                )

            # ===== CREAR VISITA AUTOMÁTICA (si el proyecto lo requiere) =====
            if proyecto_vinculado:
                try:
                    tipo_visita_auto = TipoVisita.objects.get(id=20)
                    nombre_visita = "Visita Inicial"

                    visita_automatica = Visita.objects.create(
                        paciente=paciente_nuevo,
                        nombre=nombre_visita,
                        Tipo_visita=tipo_visita_auto,
                        fecha=timezone.now().date(),
                    )

                    # Crear los exámenes asociados según el tipo de visita
                    examenes_config = getattr(tipo_visita_auto, "examenes", None)
                    logger.debug(
                        "examenes_config para tipo_visita_auto %s: %s",
                        tipo_visita_auto.id,
                        examenes_config,
                    )
                    
                    if examenes_config and isinstance(examenes_config, (list, tuple)):
                        examenes_creados = 0
                        for examen_data in examenes_config:
                            try:
                                # Convertir ID de string a int si es necesario
                                examen_id = examen_data["id"]
                                if isinstance(examen_id, str):
                                    examen_id = int(examen_id)
                                
                                examen = Examen.objects.get(id=examen_id)
                                VisitaExamen.objects.create(
                                    visita=visita_automatica,
                                    examen=examen,
                                    estado="pendiente",
                                )
                                examenes_creados += 1
                                logger.debug(
                                    "Examen %s asociado a visita automática",
                                    examen_id,
                                )
                            except Examen.DoesNotExist:
                                logger.warning(
                                    "Examen ID %s no existe (tipo_visita=%s)",
                                    examen_data.get("id"),
                                    tipo_visita_auto.id,
                                )
                            except (ValueError, TypeError) as e:
                                logger.error(
                                    "Error al parsear ID de examen %s: %s",
                                    examen_data.get("id"),
                                    e,
                                )
                            except Exception as e:
                                logger.error(
                                    "Error al asociar examen %s a visita automática: %s",
                                    examen_data.get("id"),
                                    e,
                                )
                        logger.debug(
                            "Se crearon %d exámenes para la visita automática",
                            examenes_creados,
                        )
                    elif examenes_config:
                        logger.warning(
                            "examenes_config no es una lista válida: tipo=%s, valor=%s",
                            type(examenes_config),
                            examenes_config,
                        )

                    logger.info(
                        "Visita automática '%s' creada para paciente %s (proyecto '%s')",
                        nombre_visita,
                        paciente_nuevo.id,
                        proyecto_vinculado.nombre,
                    )
                except TipoVisita.DoesNotExist:
                    logger.error(
                        "TipoVisita ID 20 ('Caracterización sueño') no existe. No se pudo crear visita automática para paciente %s.",
                        paciente_nuevo.id,
                    )
                except Exception as e:
                    logger.error(
                        "Error al crear visita automática para paciente %s: %s",
                        paciente_nuevo.id,
                        e,
                    )
            # ===== FIN VINCULACIÓN Y VISITA AUTOMÁTICA =====

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
                "token": generar_token_paciente(paciente_nuevo.id),
                "proyecto_id": proyecto_vinculado.id if proyecto_vinculado else None,
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
                    "url": f"/guardar-examen-publico-epworth/?token={generar_token_paciente(paciente.id)}",
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
                    "url": f"/guardar-examen-publico-mew/?token={generar_token_paciente(paciente.id)}",
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
                    "url": f"/guardar-examen-publico-pitsburg/?token={generar_token_paciente(paciente.id)}",
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


