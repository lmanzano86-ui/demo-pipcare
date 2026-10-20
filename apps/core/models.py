from django_tenants.models import TenantMixin, DomainMixin
from django.db import models


class Clinic(TenantMixin):
    """Cada clínica = un tenant = un schema de PostgreSQL. Aislamiento total de datos."""

    PLAN_CHOICES = [
        ("esencial", "Esencial ($249/mes — 1 proveedor)"),
        ("crecimiento", "Crecimiento ($399/mes — 2-3 proveedores)"),
        ("total", "Total ($549/mes — 4+ proveedores / multi-sede)"),
    ]
    STATUS_CHOICES = [
        ("trial", "Prueba"),
        ("active", "Activa"),
        ("suspended", "Suspendida"),
        ("cancelled", "Cancelada"),
    ]

    name = models.CharField("nombre", max_length=200)
    npi = models.CharField("NPI", max_length=20, blank=True)
    tax_id = models.CharField("Tax ID", max_length=20, blank=True)
    phone = models.CharField("teléfono", max_length=30, blank=True)
    address = models.TextField("dirección", blank=True)
    plan = models.CharField("plan", max_length=20, choices=PLAN_CHOICES, default="esencial")
    status = models.CharField("estado", max_length=20, choices=STATUS_CHOICES, default="trial")
    created_at = models.DateTimeField(auto_now_add=True)

    # === Cumplimiento regulatorio (HIPAA + FL Health Care Clinic Act) ===
    # HIPAA: el vendor SaaS es Business Associate; sin BAA firmado no debe
    # procesarse PHI real en este tenant (45 CFR 164.502(e), 164.504(e)).
    baa_signed = models.BooleanField("BAA firmado", default=False)
    baa_signed_date = models.DateField("fecha de firma del BAA", null=True, blank=True)
    # HIPAA R-06: los SMS llevan nombre del paciente + cita (ePHI). Twilio es
    # subcontratista: sin su BAA firmado, el sistema NO envía SMS reales.
    twilio_baa_signed = models.BooleanField("BAA de Twilio firmado", default=False)
    twilio_baa_date = models.DateField("fecha BAA Twilio", null=True, blank=True)
    # FL 400.990-400.999: licencia AHCA o exención documentada + director médico.
    ahca_license_number = models.CharField("licencia AHCA", max_length=50, blank=True)
    ahca_license_expires = models.DateField("vencimiento licencia AHCA", null=True, blank=True)
    license_exempt = models.BooleanField("exenta de licencia (documentado)", default=False)
    exemption_notes = models.TextField("fundamento de exención", blank=True)
    medical_director_name = models.CharField("director médico", max_length=200, blank=True)
    medical_director_license = models.CharField("licencia del director médico", max_length=50, blank=True)

    def __str__(self):
        return self.name

    def compliance_checklist(self):
        """Requisitos del tenant antes de operar con datos reales."""
        from datetime import date
        today = date.today()
        lic_ok = bool(self.ahca_license_number) or self.license_exempt
        lic_vigente = (
            self.license_exempt
            or (self.ahca_license_expires and self.ahca_license_expires >= today)
        )
        return [
            ("BAA firmado con el proveedor SaaS", self.baa_signed),
            ("Licencia AHCA vigente o exención documentada", bool(lic_ok and lic_vigente)),
            ("Director médico registrado", bool(self.medical_director_name)),
        ]


class Domain(DomainMixin):
    pass
