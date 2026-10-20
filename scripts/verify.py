"""Verificación end-to-end: crea datos en la clínica demo y comprueba aislamiento."""
import os
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth.models import User
from core.models import Clinic
from patients.models import Patient, Accident
from clinical.models import Visit, SoapNote
from billing.models import Claim, ClaimLine

with schema_context("clinica_demo"):
    user, _ = User.objects.get_or_create(username="doctor", defaults={
        "first_name": "Ana", "last_name": "Ríos", "is_staff": True})
    patient, _ = Patient.objects.get_or_create(
        first_name="Juan", last_name="Pérez", date_of_birth=date(1985, 3, 12),
        defaults={"phone": "(813) 555-0199"})
    accident, _ = Accident.objects.get_or_create(
        patient=patient, date=date(2026, 10, 10),
        defaults={"description": "Choque por alcance", "auto_insurer": "State Farm",
                  "oir_b1_1571_signed": True, "assignment_of_benefits_signed": True})
    visit, _ = Visit.objects.get_or_create(
        accident=accident, date=date(2026, 10, 16), provider=user,
        defaults={"visit_type": "initial"})
    SoapNote.objects.get_or_create(
        visit=visit,
        defaults={"subjective": "Dolor cervical 7/10",
                  "objective": "Espasmo paravertebral, ROM limitado",
                  "assessment": "S13.4XXA esguince cervical",
                  "plan": "98941 + 97140, 3x/semana"})
    claim, _ = Claim.objects.get_or_create(
        visit=visit, defaults={"status": "ready", "payer": "State Farm PIP"})
    ClaimLine.objects.get_or_create(
        claim=claim, cpt_code="98941",
        defaults={"date_of_service": date(2026, 10, 16), "modifier_1": "AT",
                  "icd10_code": "S13.4XXA", "diagnosis_pointer": "A",
                  "units": 1, "charge": 75.00})
    ClaimLine.objects.get_or_create(
        claim=claim, cpt_code="97140",
        defaults={"date_of_service": date(2026, 10, 16),
                  "icd10_code": "S13.4XXA", "diagnosis_pointer": "A",
                  "units": 1, "charge": 55.00})

    print("pacientes:", Patient.objects.count())
    print("reclamos:", Claim.objects.count())
    print("total reclamo #1: $", claim.total)
    print("historial (audit):", claim.history.count(), "entradas")

# Aislamiento: el schema público no debe ver datos del tenant
with schema_context("public"):
    print("clínicas registradas:", Clinic.objects.count())
    try:
        print("pacientes en public:", Patient.objects.count())
    except Exception as e:
        print("public sin tabla patients (correcto):", type(e).__name__)
