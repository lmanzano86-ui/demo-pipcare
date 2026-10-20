"""Crea el tenant público y una clínica demo con su dominio."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))  # config
sys.path.insert(0, str(BASE_DIR / "apps"))  # apps
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from core.models import Clinic, Domain

public, _ = Clinic.objects.get_or_create(
    schema_name="public",
    defaults={"name": "Plataforma (schema público)"},
)
Domain.objects.get_or_create(domain="localhost", defaults={"tenant": public, "is_primary": True})

demo, created = Clinic.objects.get_or_create(
    schema_name="clinica_demo",
    defaults={
        "name": "Clínica Demo Accidentes",
        "npi": "1234567890",
        "tax_id": "12-3456789",
        "phone": "(813) 555-0100",
        "plan": "crecimiento",
        "status": "active",
    },
)
Domain.objects.get_or_create(
    domain="clinica-demo.localhost",
    defaults={"tenant": demo, "is_primary": True},
)

# Usuario admin para la clínica demo (solo si no existe)
from django_tenants.utils import schema_context
from django.contrib.auth.models import User

with schema_context("clinica_demo"):
    if not User.objects.filter(username="admin").exists():
        u = User.objects.create_superuser("admin", "admin@example.com", "admin123")
        print("usuario creado: admin / admin123")
    else:
        u = User.objects.get(username="admin")
        print("usuario admin ya existía")
    # El admin demo es administrador de la clínica (rol para control de acceso).
    from accounts.models import Profile
    Profile.objects.get_or_create(user=u, defaults={"role": "admin"})

print(f"demo creada: {created} | schema: {demo.schema_name}")
