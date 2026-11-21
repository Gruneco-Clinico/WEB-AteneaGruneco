# -*- encoding: utf-8 -*-
"""
Muestra una muestra de franjas del cruce Anosognosia × PostHog por horario
para revisión manual de falsos positivos (horario_unico) y contaminación
(personal / dispositivos compartidos).

No imprime nombres ni correos de pacientes: solo IDs internos, N/M y person_ids.

Usage:
    python manage.py auditar_cruce_anosognosia_horario
    python manage.py auditar_cruce_anosognosia_horario --limite 15 --origen horario_unico
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.home.services import recuerdame_anosognosia_cruce as cruce


class Command(BaseCommand):
    help = (
        "Audita una muestra de franjas del cruce Anosognosia (scope/confianza PostHog)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limite",
            type=int,
            default=20,
            help="Máximo de franjas a listar por origen (default 20).",
        )
        parser.add_argument(
            "--origen",
            type=str,
            default="",
            help="Filtrar por match_origen (email, horario_unico, horario_grupo).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Salida JSON (sin texto narrativo).",
        )

    def handle(self, *args, **options):
        self.stdout.write("Construyendo cruce (puede consultar PostHog)…")
        datos = cruce.construir_cruce()
        franjas = datos.get("franjas") or []
        origen = (options.get("origen") or "").strip()
        if origen:
            franjas = [f for f in franjas if f.get("match_origen") == origen]

        # Priorizar unicos y grupos para la muestra
        unicos = [f for f in franjas if f.get("match_origen") == "horario_unico"]
        grupos = [f for f in franjas if f.get("match_origen") == "horario_grupo"]
        limite = options["limite"]

        muestra = {
            "date_from": datos.get("date_from"),
            "date_to": datos.get("date_to"),
            "kpis": datos.get("kpis"),
            "checklist": [
                "¿El person_id de horario_unico corresponde a un participante y no a staff?",
                "¿Hay tablets/sala compartidas que concentren eventos en la franja?",
                "En horario_grupo, ¿n_personas ≈ n_pacientes o hay sobreconteo (bots/acompañantes)?",
                "¿Algún horario_unico cae fuera del bloque real de intervención?",
            ],
            "horario_unico": unicos[:limite],
            "horario_grupo": grupos[:limite],
            "nota": (
                "Estimación de FP: revisar manualmente horario_unico y registrar "
                "en docs/issues/ la tasa observada. No pegar datos identificables."
            ),
        }

        if options["json"]:
            self.stdout.write(json.dumps(muestra, ensure_ascii=False, indent=2, default=str))
            return

        self.stdout.write(self.style.NOTICE("Checklist de auditoría:"))
        for item in muestra["checklist"]:
            self.stdout.write(f"  - [ ] {item}")

        kpis = muestra["kpis"] or {}
        self.stdout.write("")
        self.stdout.write(
            f"Periodo {muestra['date_from']} → {muestra['date_to']} | "
            f"único={kpis.get('con_match_horario_unico')} "
            f"grupo_sesiones={kpis.get('sesiones_horario_grupo')} "
            f"no_atribuible={kpis.get('sesiones_no_atribuible')}"
        )

        def _volcar(titulo, items):
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(titulo))
            if not items:
                self.stdout.write("  (sin franjas)")
                return
            for f in items:
                pids = ",".join((f.get("person_ids") or [])[:8])
                if len(f.get("person_ids") or []) > 8:
                    pids += ",…"
                self.stdout.write(
                    f"  {f.get('fecha')} {f.get('hora_inicio')}-{f.get('hora_final')} "
                    f"N={f.get('n_pacientes')} M={f.get('n_personas')} "
                    f"scope={f.get('match_scope')} conf={f.get('match_confianza')} "
                    f"atr={f.get('atribuible')} ids=[{pids}]"
                )

        if origen:
            filtradas = franjas[:limite]
            _volcar(f"Franjas origen={origen}", filtradas)
        else:
            _volcar("Muestra horario_unico", muestra["horario_unico"])
            _volcar("Muestra horario_grupo", muestra["horario_grupo"])

        self.stdout.write("")
        self.stdout.write(muestra["nota"])
        if datos.get("error_posthog"):
            self.stdout.write(self.style.WARNING(f"PostHog: {datos['error_posthog']}"))
        if datos.get("error_activity"):
            self.stdout.write(self.style.WARNING(f"Activity: {datos['error_activity']}"))
