#!/usr/bin/env bash
# Arranque de la DEMO en hosting (Render): migraciones + seed + gunicorn.
# Idempotente: seguro de correr en cada despliegue o reinicio del servicio.
set -e

python manage.py migrate_schemas
python scripts/seed.py

python manage.py shell <<'PYEOF'
import os
from core.models import Clinic, Domain
from django_tenants.utils import schema_context
from django.contrib.auth.models import User
from accounts.models import Profile

host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "demo-pipcare.onrender.com")
demo = Clinic.objects.get(schema_name="clinica_demo")
Domain.objects.get_or_create(domain=host, defaults={"tenant": demo, "is_primary": False})

with schema_context("clinica_demo"):
    u, created = User.objects.get_or_create(
        username="demo", defaults={"email": "demo@example.com"}
    )
    if created:
        u.set_password("demo123")
        u.save()
        print("usuario demo/demo123 creado")
    Profile.objects.get_or_create(user=u, defaults={"role": "frontdesk"})
print("dominio del tenant listo:", host)
PYEOF

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
