"""Prueba el flujo MVP: admisión -> visita -> SOAP -> reclamo -> PDF."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.test import Client
from django_tenants.utils import schema_context
from django.contrib.auth.models import User

HOST = "clinica-demo.localhost"

with schema_context("clinica_demo"):
    u = User.objects.get(username="doctor")
    u.set_password("demo1234")
    u.save()

c = Client(HTTP_HOST=HOST)
r = c.post("/accounts/login/", {"username": "doctor", "password": "demo1234"})
assert r.status_code == 302, f"login falló: {r.status_code}"
print("1. login OK")

r = c.get("/intake/")
assert r.status_code == 200, r.status_code
print("2. GET admisión OK")

r = c.post("/intake/", {
    "p-first_name": "María", "p-last_name": "Gómez",
    "p-date_of_birth": "1990-05-20", "p-phone": "(813) 555-0142",
    "p-email": "", "p-address": "123 Main St, Tampa FL",
    "a-date": "2026-10-12", "a-accident_type": "auto",
    "a-description": "Choque lateral", "a-auto_insurer": "GEICO",
    "a-policy_number": "POL-999", "a-oir_b1_1571_signed": "on",
    "a-assignment_of_benefits_signed": "on",
})
assert r.status_code == 302, r.status_code
accident_url = r["Location"]
print("3. POST admisión OK ->", accident_url)

accident_pk = accident_url.strip("/").split("/")[-1]
r = c.post(f"/accidente/{accident_pk}/visita/nueva/",
           {"date": "2026-10-16", "provider": u.pk, "visit_type": "initial"})
assert r.status_code == 302, r.status_code
soap_url = r["Location"]
print("4. POST visita OK ->", soap_url)

visit_pk = soap_url.strip("/").split("/")[-2]
r = c.post(f"/visita/{visit_pk}/soap/", {
    "subjective": "Dolor lumbar 8/10", "objective": "Espasmo, ROM limitado",
    "assessment": "S33.5XXA", "plan": "98941 3x/semana"})
assert r.status_code == 302, r.status_code
print("5. POST SOAP OK")

r = c.get(f"/visita/{visit_pk}/reclamo/nuevo/")
assert r.status_code == 302, r.status_code
claim_url = r["Location"]
claim_pk = claim_url.strip("/").split("/")[-1]
print("6. reclamo creado ->", claim_url)

r = c.post(f"/reclamo/{claim_pk}/linea/nueva/", {
    "date_of_service": "2026-10-16", "cpt_code": "98941",
    "modifier_1": "AT", "icd10_code": "S33.5XXA",
    "diagnosis_pointer": "A", "units": 1, "charge": "85.00"})
assert r.status_code == 302, r.status_code
print("7. línea CPT agregada OK")

r = c.get(f"/reclamo/{claim_pk}/pdf/")
assert r.status_code == 200 and r["Content-Type"] == "application/pdf", r.status_code
pdf_bytes = b"".join(r.streaming_content)
assert pdf_bytes[:5] == b"%PDF-", "no es PDF"
open("/tmp/cms1500-test.pdf", "wb").write(pdf_bytes)
print(f"8. PDF CMS-1500 OK ({len(pdf_bytes)} bytes) -> /tmp/cms1500-test.pdf")

r = c.get("/")
assert "Clínica Demo" in r.content.decode(), "tenant no resuelto"
print("9. tenant resuelto en home OK")
print("\nFLUJO COMPLETO: ✅")
