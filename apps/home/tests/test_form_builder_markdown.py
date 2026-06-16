# -*- encoding: utf-8 -*-
from django.test import SimpleTestCase

from apps.home.form_builder.markdown import render_safe_markdown
from apps.home.templatetags.form_builder_tags import fb_markdown


class RenderSafeMarkdownTests(SimpleTestCase):
    def test_empty_returns_empty(self):
        self.assertEqual(render_safe_markdown(""), "")
        self.assertEqual(render_safe_markdown("   "), "")

    def test_bold_and_paragraph(self):
        html = render_safe_markdown("**Importante:** texto")
        self.assertIn("<strong>Importante:</strong>", html)

    def test_list(self):
        html = render_safe_markdown("- uno\n- dos")
        self.assertIn("<ul>", html)
        self.assertIn("<li>uno</li>", html)

    def test_strips_script_tags(self):
        html = render_safe_markdown("<script>alert(1)</script>\n\n**ok**")
        self.assertNotIn("<script>", html)
        self.assertIn("<strong>ok</strong>", html)

    def test_strips_markdown_links(self):
        html = render_safe_markdown("[x](javascript:alert(1))")
        self.assertNotIn("javascript:", html)
        self.assertNotIn("<a", html)

    def test_fb_markdown_filter_matches_helper(self):
        self.assertEqual(
            str(fb_markdown("**hola**")),
            render_safe_markdown("**hola**"),
        )
