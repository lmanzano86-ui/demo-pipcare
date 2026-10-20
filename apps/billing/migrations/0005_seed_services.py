"""Catálogo inicial de servicios frecuentes en clínicas de accidentes.

La clínica puede editarlos, desactivarlos o agregar los suyos. Corre por
schema (cada clínica tiene su catálogo).
"""

from django.db import migrations
from decimal import Decimal

DEFAULT_SERVICES = [
    # code, name, category, cpt, mod1, mod2, icd10, pointer, units, charge, duration
    ("EV-INICIAL", "Evaluación inicial", "visita", "99203", "", "", "S13.4XXA", "A", 1, Decimal("250.00"), 45),
    ("EV-SEGUIM", "Visita de seguimiento", "visita", "99213", "", "", "S13.4XXA", "A", 1, Decimal("120.00"), 20),
    ("REEXAM", "Reexaminación", "visita", "99214", "", "", "S13.4XXA", "A", 1, Decimal("150.00"), 30),
    ("AJUSTE", "Ajuste quiropráctico", "quiro", "98941", "AT", "", "M54.2", "A", 1, Decimal("75.00"), 15),
    ("TERAPIA", "Ejercicio terapéutico", "terapia", "97110", "", "", "M54.2", "A", 1, Decimal("60.00"), 30),
    ("MAS-TER", "Terapia manual / masaje terapéutico", "terapia", "97140", "", "", "M54.2", "A", 1, Decimal("65.00"), 20),
]


def seed_services(apps, schema_editor):
    Service = apps.get_model("billing", "Service")
    for code, name, cat, cpt, m1, m2, icd, ptr, units, charge, dur in DEFAULT_SERVICES:
        Service.objects.get_or_create(
            code=code,
            defaults={"name": name, "category": cat, "default_cpt": cpt,
                      "default_modifier_1": m1, "default_modifier_2": m2,
                      "default_icd10": icd, "default_diagnosis_pointer": ptr,
                      "default_units": units, "default_charge": charge,
                      "duration_min": dur, "is_active": True},
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [("billing", "0004_service_historicalservice")]

    operations = [migrations.RunPython(seed_services, noop)]
