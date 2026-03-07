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
from django.db.models import Max, Count, Q
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

logger = logging.getLogger(__name__)

def is_superuser(user):
    return user.is_superuser


@login_required
def generar_pdf_examen_generico(request, visita_examen_id):
    context = {"segment": "home"}
    html_template = loader.get_template("home/home-page.html")
    return HttpResponse(html_template.render(context, request))


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
    user = request.user

    # Total visits where user is evaluador
    total_visitas = Visita.objects.filter(evaluador=user).count()

    # Distinct patients seen
    total_pacientes = (
        Visita.objects.filter(evaluador=user)
        .values("paciente")
        .distinct()
        .count()
    )

    # Visits per project
    visitas_por_proyecto = (
        Visita.objects.filter(evaluador=user, Tipo_visita__proyecto__isnull=False)
        .values("Tipo_visita__proyecto__id", "Tipo_visita__proyecto__nombre")
        .annotate(
            num_visitas=Count("id"),
            num_pacientes=Count("paciente", distinct=True),
        )
        .order_by("-num_visitas")
    )

    stats_proyecto = [
        {
            "nombre": item["Tipo_visita__proyecto__nombre"],
            "num_visitas": item["num_visitas"],
            "num_pacientes": item["num_pacientes"],
        }
        for item in visitas_por_proyecto
    ]

    context = {
        "total_visitas": total_visitas,
        "total_pacientes": total_pacientes,
        "stats_proyecto": stats_proyecto,
    }
    return render(request, "home/profile.html", context)


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


# gestion de usuarios #########################################################
@login_required
@user_passes_test(is_superuser, login_url="/login/")
def administrar_usuarios(request):
    """Vista centralizada para administrar usuarios del sistema"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect("index")

    # Obtener lista de usuarios
    usuarios_list = User.objects.all().order_by("-date_joined")

    # Estadísticas: pacientes vistos por usuario por proyecto
    stats_usuario_proyecto = (
        Visita.objects.filter(evaluador__isnull=False, Tipo_visita__proyecto__isnull=False)
        .values(
            "evaluador__id",
            "evaluador__username",
            "evaluador__first_name",
            "evaluador__last_name",
            "Tipo_visita__proyecto__nombre",
        )
        .annotate(
            num_pacientes=Count("paciente", distinct=True),
            num_visitas=Count("id"),
        )
        .order_by("evaluador__username", "Tipo_visita__proyecto__nombre")
    )

    # Preparar contexto inicial
    context = {
        "usuarios": usuarios_list,
        "total_usuarios": usuarios_list.count(),
        "usuarios_activos": usuarios_list.filter(is_active=True).count(),
        "administradores": usuarios_list.filter(is_superuser=True).count(),
        "stats_usuario_proyecto": list(stats_usuario_proyecto),
    }

    # === PROCESAMIENTO DE ACCIONES ===
    if request.method == "POST":
        accion = request.POST.get("accion_usuario")

        # --- ACCIÓN: REGISTRAR NUEVO USUARIO ---
        if accion == "registrar":
            return _procesar_registro_usuario(request, context)

        # --- ACCIÓN: MODIFICAR USUARIO EXISTENTE ---
        elif accion == "modificar":
            return _procesar_modificacion_usuario(request, context)

        # --- ACCIÓN: ELIMINAR USUARIO ---
        elif accion == "eliminar":
            return _procesar_eliminacion_usuario(request)

        # --- ACCIÓN: GUARDAR FIRMA DEL SUPERUSUARIO ---
        elif accion == "guardar_firma":
            return guardar_firma_usuario(request)

    # GET - mostrar interfaz principal
    return render(request, "home/administrar_usuarios.html", context)

@login_required
def _procesar_registro_usuario(request, context):
    """Función auxiliar para procesar registro de nuevo usuario"""
    try:
        # Recopilar datos del formulario
        datos_usuario = {
            "username": request.POST.get("username_nuevo"),
            "email": request.POST.get("email_nuevo"),
            "password": request.POST.get("password_nuevo"),
            "confirm_password": request.POST.get("confirmar_password"),
            "first_name": request.POST.get("nombre_usuario", ""),
            "last_name": request.POST.get("apellido_usuario", ""),
        }

        # Configuración de permisos
        permisos_usuario = {
            "is_superuser": request.POST.get("admin_permisos") == "on",
            "is_staff": request.POST.get("staff_permisos") == "on",
            "is_active": request.POST.get("activo_estado") == "on",
        }

        # Validar campos obligatorios
        if not all(
            [
                datos_usuario["username"],
                datos_usuario["email"],
                datos_usuario["password"],
            ]
        ):
            messages.error(request, "❌ Los campos básicos son obligatorios.")
            return render(request, "home/administrar_usuarios.html", context)

        # Validar coincidencia de contraseñas
        if datos_usuario["password"] != datos_usuario["confirm_password"]:
            messages.error(request, "❌ Las contraseñas no son idénticas.")
            return render(request, "home/administrar_usuarios.html", context)

        # Validar longitud de contraseña
        if len(datos_usuario["password"]) < 8:
            messages.error(request, "❌ La contraseña requiere mínimo 8 caracteres.")
            return render(request, "home/administrar_usuarios.html", context)

        # Verificar unicidad del username
        if User.objects.filter(username=datos_usuario["username"]).exists():
            messages.error(request, "❌ Este nombre de usuario ya está registrado.")
            return render(request, "home/administrar_usuarios.html", context)

        # Verificar unicidad del email
        if User.objects.filter(email=datos_usuario["email"]).exists():
            messages.error(request, "❌ Este correo electrónico ya está en uso.")
            return render(request, "home/administrar_usuarios.html", context)

        # Crear nuevo usuario
        nuevo_usuario = User.objects.create_user(
            username=datos_usuario["username"],
            email=datos_usuario["email"],
            password=datos_usuario["password"],
            first_name=datos_usuario["first_name"],
            last_name=datos_usuario["last_name"],
            **permisos_usuario,
        )

        # Generar descripción de tipo de usuario
        tipos_asignados = []
        if permisos_usuario["is_superuser"]:
            tipos_asignados.append("Administrador")
        if permisos_usuario["is_staff"]:
            tipos_asignados.append("Personal")
        if not permisos_usuario["is_active"]:
            tipos_asignados.append("Desactivado")

        descripcion_tipo = (
            " - ".join(tipos_asignados) if tipos_asignados else "Usuario básico"
        )

        messages.success(
            request,
            f"✅ Usuario '{datos_usuario['username']}' registrado correctamente.\n"
            f"📧 Correo: {datos_usuario['email']}\n"
            f"🔐 Tipo: {descripcion_tipo}",
        )

        return redirect("administrar_usuarios")

    except Exception as e:
        messages.error(request, f"❌ Error durante el registro: {str(e)}")
        return render(request, "home/administrar_usuarios.html", context)

@login_required
def _procesar_modificacion_usuario(request, context):
    """Función auxiliar para procesar modificación de usuario"""
    try:
        user_id = request.POST.get("usuario_id")
        usuario_objetivo = get_object_or_404(User, id=user_id)

        # Datos de modificación
        nuevo_username = request.POST.get("username_modificar")
        nuevo_email = request.POST.get("email_modificar")
        nuevo_nombre = request.POST.get("nombre_modificar", "")
        nuevo_apellido = request.POST.get("apellido_modificar", "")

        # Nuevos permisos
        nuevo_admin = request.POST.get("admin_modificar") == "on"
        nuevo_staff = request.POST.get("staff_modificar") == "on"
        nuevo_activo = request.POST.get("activo_modificar") == "on"

        # Contraseña nueva (opcional)
        nueva_password = request.POST.get("nueva_password_modificar", "")
        confirmar_nueva = request.POST.get("confirmar_nueva_modificar", "")

        # Validaciones básicas
        if not nuevo_username or not nuevo_email:
            messages.error(request, "❌ Username y email son campos requeridos.")
            return render(request, "home/administrar_usuarios.html", context)

        # Verificar username único (excluyendo usuario actual)
        if User.objects.filter(username=nuevo_username).exclude(id=user_id).exists():
            messages.error(
                request, "❌ Este username ya está ocupado por otro usuario."
            )
            return render(request, "home/administrar_usuarios.html", context)

        # Verificar email único (excluyendo usuario actual)
        if User.objects.filter(email=nuevo_email).exclude(id=user_id).exists():
            messages.error(request, "❌ Este email ya está usado por otro usuario.")
            return render(request, "home/administrar_usuarios.html", context)

        # Validar nueva contraseña si se proporcionó
        if nueva_password:
            if nueva_password != confirmar_nueva:
                messages.error(request, "❌ Las nuevas contraseñas no coinciden.")
                return render(request, "home/administrar_usuarios.html", context)

            if len(nueva_password) < 8:
                messages.error(
                    request, "❌ La nueva contraseña debe tener mínimo 8 caracteres."
                )
                return render(request, "home/administrar_usuarios.html", context)

        # Aplicar modificaciones
        usuario_objetivo.username = nuevo_username
        usuario_objetivo.email = nuevo_email
        usuario_objetivo.first_name = nuevo_nombre
        usuario_objetivo.last_name = nuevo_apellido
        usuario_objetivo.is_superuser = nuevo_admin
        usuario_objetivo.is_staff = nuevo_staff
        usuario_objetivo.is_active = nuevo_activo

        # Cambiar contraseña si se proporcionó
        if nueva_password:
            usuario_objetivo.set_password(nueva_password)

        usuario_objetivo.save()

        messages.success(
            request, f"✅ Usuario '{nuevo_username}' modificado correctamente."
        )
        return redirect("administrar_usuarios")

    except Exception as e:
        messages.error(request, f"❌ Error durante la modificación: {str(e)}")
        return render(request, "home/administrar_usuarios.html", context)

@login_required
def _procesar_eliminacion_usuario(request):
    """Función auxiliar para procesar eliminación de usuario"""
    try:
        user_id = request.POST.get("usuario_id")
        usuario_objetivo = get_object_or_404(User, id=user_id)

        # Prevenir auto-eliminación
        if usuario_objetivo.id == request.user.id:
            messages.error(request, "❌ No es posible eliminar tu propia cuenta.")
            return redirect("administrar_usuarios")

        username_eliminado = usuario_objetivo.username
        usuario_objetivo.delete()

        messages.success(
            request, f"✅ Usuario '{username_eliminado}' eliminado del sistema."
        )

    except Exception as e:
        messages.error(request, f"❌ Error durante la eliminación: {str(e)}")

    return redirect("administrar_usuarios")


@login_required
def guardar_firma_usuario(request):
    if request.method == "POST" and request.POST.get("accion_usuario") == "guardar_firma":
        try:
            user = request.user
            perfil, _ = UserProfile.objects.get_or_create(user=user)

            imagen = request.FILES.get("firma_imagen")
            imagen_url = (request.POST.get("firma_imagen_url") or "").strip()
            firma_texto = (request.POST.get("firma_usuario") or "").strip()

            if imagen:
                contenido = imagen.read()
                mime = getattr(imagen, "content_type", "image/png")
                base64_img = base64.b64encode(contenido).decode("utf-8")
                perfil.firma = f"data:{mime};base64,{base64_img}"

            elif imagen_url:
                # Intentar descargar con timeout; manejar errores
                try:
                    resp = requests.get(imagen_url, timeout=5)
                    if resp.status_code == 200 and resp.content:
                        mime = resp.headers.get("Content-Type", "image/png")
                        base64_img = base64.b64encode(resp.content).decode("utf-8")
                        perfil.firma = f"data:{mime};base64,{base64_img}"
                    else:
                        messages.error(request, "No se pudo descargar la imagen desde la URL proporcionada.")
                        return redirect(request.META.get("HTTP_REFERER", "/"))
                except Exception as e:
                    logging.exception("Error descargando imagen de firma: %s", e)
                    messages.error(request, "Error descargando la imagen de la URL. Ver logs.")
                    return redirect(request.META.get("HTTP_REFERER", "/"))

            elif firma_texto:
                perfil.firma = firma_texto

            else:
                # Nada enviado
                messages.error(request, "No se proporcionó imagen ni texto para la firma.")
                return redirect(request.META.get("HTTP_REFERER", "/"))

            perfil.save()
            messages.success(request, "Firma guardada correctamente.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        except Exception as e:
            logging.exception("Error guardando firma de usuario: %s", e)
            messages.error(request, f"Error guardando la firma: {str(e)}")
            return redirect(request.META.get("HTTP_REFERER", "/"))

# dashboard
@login_required(login_url="/login/")
def index(request):
    context = {"segment": "index"}
    html_template = loader.get_template("home/index.html")
    return HttpResponse(html_template.render(context, request))


