# -*- encoding: utf-8 -*-
"""
Tests for apps.home.decorators — role-based access control.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views import View

from apps.home.decorators import (
    role_required,
    RoleRequiredMixin,
    ROLES,
    _user_has_role,
)


class RoleHelperTests(TestCase):
    """Tests for _user_has_role utility."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.group_admin, _ = Group.objects.get_or_create(name="Administrador")
        self.group_inv, _ = Group.objects.get_or_create(name="Investigador")

    def test_superuser_bypasses_role_check(self):
        self.user.is_superuser = True
        self.user.save()
        self.assertTrue(_user_has_role(self.user, ["Evaluador"]))

    def test_user_with_matching_group_passes(self):
        self.user.groups.add(self.group_admin)
        self.assertTrue(_user_has_role(self.user, ["Administrador"]))

    def test_user_without_matching_group_fails(self):
        self.user.groups.add(self.group_inv)
        self.assertFalse(_user_has_role(self.user, ["Administrador"]))

    def test_user_with_no_groups_fails(self):
        self.assertFalse(_user_has_role(self.user, ["Administrador"]))

    def test_multiple_roles_match_any(self):
        self.user.groups.add(self.group_inv)
        self.assertTrue(
            _user_has_role(self.user, ["Administrador", "Investigador"])
        )


class RoleRequiredDecoratorTests(TestCase):
    """Tests for @role_required decorator."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.group_admin, _ = Group.objects.get_or_create(name="Administrador")

        @role_required("Administrador")
        def protected_view(request):
            return HttpResponse("OK")

        self.protected_view = protected_view

    def test_user_with_role_gets_200(self):
        self.user.groups.add(self.group_admin)
        request = self.factory.get("/test/")
        request.user = self.user
        response = self.protected_view(request)
        self.assertEqual(response.status_code, 200)

    def test_user_without_role_gets_403(self):
        request = self.factory.get("/test/")
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            self.protected_view(request)

    def test_superuser_bypasses(self):
        self.user.is_superuser = True
        self.user.save()
        request = self.factory.get("/test/")
        request.user = self.user
        response = self.protected_view(request)
        self.assertEqual(response.status_code, 200)

    def test_no_roles_raises_value_error(self):
        with self.assertRaises(ValueError):
            role_required()


class RoleRequiredMixinTests(TestCase):
    """Tests for RoleRequiredMixin on class-based views."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.group_eval, _ = Group.objects.get_or_create(name="Evaluador")

        class ProtectedView(RoleRequiredMixin, View):
            required_roles = ["Evaluador"]

            def get(self, request):
                return HttpResponse("OK")

        self.view_cls = ProtectedView

    def test_user_with_role_gets_200(self):
        self.user.groups.add(self.group_eval)
        request = self.factory.get("/test/")
        request.user = self.user
        response = self.view_cls.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_user_without_role_gets_403(self):
        request = self.factory.get("/test/")
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            self.view_cls.as_view()(request)

    def test_superuser_bypasses(self):
        self.user.is_superuser = True
        self.user.save()
        request = self.factory.get("/test/")
        request.user = self.user
        response = self.view_cls.as_view()(request)
        self.assertEqual(response.status_code, 200)


class DefaultRolesConstantTests(TestCase):
    """Ensure the canonical ROLES tuple is correct."""

    def test_roles_contains_three_entries(self):
        self.assertEqual(len(ROLES), 3)

    def test_roles_names(self):
        self.assertIn("Administrador", ROLES)
        self.assertIn("Investigador", ROLES)
        self.assertIn("Evaluador", ROLES)
