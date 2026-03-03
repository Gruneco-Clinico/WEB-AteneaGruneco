# -*- encoding: utf-8 -*-
"""
Role-based access control decorators and mixins for ATENEA.

Usage (function-based views):
    @login_required
    @role_required("Administrador", "Investigador")
    def mi_vista(request):
        ...

Usage (class-based views):
    class MiVista(RoleRequiredMixin, View):
        required_roles = ["Administrador", "Investigador"]
        ...

Groups/Roles:
    - Administrador: Full access, user management, project config
    - Investigador: Patient data, visits, exams, reports
    - Evaluador: Assigned exams only, read-only on other data

Superusers bypass all role checks.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical role names — single source of truth
# ---------------------------------------------------------------------------
ROLES = ("Administrador", "Investigador", "Evaluador")


def _user_has_role(user, roles):
    """Return True if *user* belongs to at least one of the listed *roles*.

    Superusers bypass the check entirely.
    """
    if user.is_superuser:
        return True
    user_groups = set(user.groups.values_list("name", flat=True))
    return bool(user_groups & set(roles))


# ---------------------------------------------------------------------------
# Function-based view decorator
# ---------------------------------------------------------------------------
def role_required(*roles):
    """Decorator that checks the user belongs to at least one of *roles*.

    Must be stacked **after** ``@login_required`` so that
    ``request.user`` is guaranteed to be authenticated::

        @login_required
        @role_required("Administrador")
        def admin_only_view(request):
            ...

    Raises ``PermissionDenied`` (HTTP 403) when the check fails.
    """

    if not roles:
        raise ValueError("role_required() requires at least one role name")

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not _user_has_role(request.user, roles):
                logger.warning(
                    "Acceso denegado: usuario=%s roles_requeridos=%s uri=%s",
                    request.user.username,
                    roles,
                    request.path,
                )
                raise PermissionDenied(
                    "No tienes permiso para acceder a esta página."
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


# ---------------------------------------------------------------------------
# Class-based view mixin
# ---------------------------------------------------------------------------
class RoleRequiredMixin(LoginRequiredMixin):
    """Mixin for class-based views that enforces role membership.

    Set ``required_roles`` on the subclass::

        class MiVista(RoleRequiredMixin, TemplateView):
            required_roles = ["Investigador", "Evaluador"]
            template_name = "mi_template.html"

    Returns HTTP 403 if the user does not belong to any of the listed roles.
    Superusers bypass the check.
    """

    required_roles: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        # LoginRequiredMixin.dispatch handles unauthenticated users
        response = super().dispatch(request, *args, **kwargs)

        # If LoginRequiredMixin already redirected, honour that
        if hasattr(response, "status_code") and response.status_code in (301, 302):
            return response

        if self.required_roles and not _user_has_role(
            request.user, self.required_roles
        ):
            logger.warning(
                "Acceso denegado (CBV): usuario=%s roles_requeridos=%s uri=%s",
                request.user.username,
                self.required_roles,
                request.path,
            )
            raise PermissionDenied(
                "No tienes permiso para acceder a esta página."
            )

        return response
