from datetime import date, timedelta

from django.db import models
from simple_history.models import HistoricalRecords


class Patient(models.Model):
    first_name = models.CharField("nombre", max_length=100)
    last_name = models.CharField("apellido", max_length=100)
    date_of_birth = models.DateField("fecha de nacimiento")
    phone = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField("dirección", blank=True)
    # TCPA: dar el número en admisión = consentimiento para recordatorios de
    # salud (no marketing). Se registra fecha y se puede revocar.
    sms_consent = models.BooleanField("consiente SMS de recordatorios", default=False)
    sms_consent_date = models.DateField("fecha del consentimiento SMS", null=True, blank=True)
    sms_consent_revoked = models.BooleanField("consentimiento SMS revocado", default=False)
    # No Surprises Act: paciente sin seguro / auto-pago requiere Good Faith Estimate.
    self_pay = models.BooleanField("auto-pago / sin seguro (requiere GFE)", default=False)
    # Firma electrónica guardada: el paciente la dibuja una vez y el sistema la
    # recuerda para aplicarla en otros documentos (cada firma sigue creando su
    # propio registro con fecha/hora/IP por documento, como exige ESIGN/UETA).
    signature_image = models.TextField("firma electrónica guardada (PNG base64)", blank=True)
    signature_saved_at = models.DateTimeField("firma guardada el", null=True, blank=True)
    # Requerido por el segmento DMG del 837P (M/F/U).
    gender = models.CharField("sexo", max_length=1, blank=True,
                              choices=[("M", "Masculino"), ("F", "Femenino"), ("U", "No especificado")])
    # Datos clínicos básicos (idea de Clinexa): contacto de emergencia y alergias.
    emergency_contact_name = models.CharField("contacto de emergencia", max_length=120, blank=True)
    emergency_contact_phone = models.CharField("teléfono de emergencia", max_length=30, blank=True)
    allergies = models.TextField("alergias", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def sms_allowed(self):
        """¿Se le puede enviar SMS de recordatorios? (TCPA)"""
        return self.sms_consent and not self.sms_consent_revoked and bool(self.phone)


class Accident(models.Model):
    """El caso: accidente que origina el tratamiento y la facturación PIP."""

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="accidents")
    date = models.DateField("fecha del accidente")
    accident_type = models.CharField("tipo", max_length=50, default="auto",
                                     choices=[("auto", "Auto"), ("work", "Laboral"), ("other", "Otro")])
    description = models.TextField("descripción", blank=True)
    claim_number = models.CharField("nº de reclamo", max_length=50, blank=True)
    auto_insurer = models.CharField("aseguradora del auto", max_length=150, blank=True)
    policy_number = models.CharField("nº de póliza", max_length=50, blank=True)
    attorney = models.CharField("abogado", max_length=150, blank=True)
    # Documentos PIP obligatorios en Florida
    oir_b1_1571_signed = models.BooleanField("OIR-B1-1571 firmado", default=False)
    assignment_of_benefits_signed = models.BooleanField("cesión de beneficios firmada", default=False)
    # FL 627.736(5)(e): disclosure & acknowledgment en el tratamiento inicial.
    # Debe firmarse de puño y letra; el original se entrega al insurer (NO electrónico).
    disclosure_5e_signed = models.BooleanField("declaración 5(e) firmada (puño y letra)", default=False)
    disclosure_5e_date = models.DateField("fecha de firma 5(e)", null=True, blank=True)
    # FL 627.736(1)(a): EMC determina el tope ($10,000 con EMC / $2,500 sin EMC).
    emc_determined = models.BooleanField("EMC determinada por MD/DO/PA/APRN", default=False)
    emc_date = models.DateField("fecha de determinación EMC", null=True, blank=True)
    # FL 627.736(5)(c): notice of initiation of treatment dentro de 21 días
    # extiende el timely filing de 35 a 75 días.
    notice_of_initiation_date = models.DateField(
        "aviso de inicio de tratamiento enviado el", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"Accidente {self.date} — {self.patient}"

    # === Motor de relojes PIP (FL 627.736) ===
    @property
    def first_visit_date(self):
        if not self.pk:
            return None
        v = self.visits.order_by("date").first()
        return v.date if v else None

    @property
    def pip_limit(self):
        return 10000 if self.emc_determined else 2500

    def deadline_14d(self):
        """El tratamiento inicial debe ocurrir dentro de 14 días del accidente."""
        return self.date + timedelta(days=14)

    def timely_filing_deadline(self):
        """35 días desde el servicio; 75 si se envió notice of initiation a tiempo."""
        base = self.first_visit_date or self.date
        if (self.notice_of_initiation_date and self.first_visit_date
                and (self.notice_of_initiation_date - self.first_visit_date).days <= 21):
            return base + timedelta(days=75)
        return base + timedelta(days=35)

    def pip_alerts(self):
        """Alertas de cumplimiento con nivel: ok / warn / bad."""
        today = date.today()
        alerts = []
        # Regla de 14 días
        if not self.first_visit_date:
            days_left = (self.deadline_14d() - today).days
            if days_left < 0:
                alerts.append(("bad", f"Regla de 14 días VENCIDA: sin tratamiento inicial, PIP no cubre."))
            elif days_left <= 3:
                alerts.append(("warn", f"Regla de 14 días: quedan {days_left} días para el tratamiento inicial."))
            else:
                alerts.append(("ok", f"Regla de 14 días: vence el {self.deadline_14d()}."))
        # Timely filing
        if self.first_visit_date:
            dl = self.timely_filing_deadline()
            days_left = (dl - today).days
            window = "75" if dl == (self.first_visit_date + timedelta(days=75)) else "35"
            if days_left < 0:
                alerts.append(("bad", f"Timely filing VENCIDO ({window} días): cargos legalmente incobrables."))
            elif days_left <= 7:
                alerts.append(("warn", f"Timely filing: quedan {days_left} días (ventana de {window} días)."))
        # Notice of initiation
        if self.first_visit_date and not self.notice_of_initiation_date:
            days_since = (today - self.first_visit_date).days
            if days_since <= 21:
                alerts.append(("warn", "Enviar notice of initiation of treatment: extiende timely filing a 75 días."))
        # Documentos
        if not self.disclosure_5e_signed:
            alerts.append(("warn", "Falta la declaración 5(e) firmada de puño y letra (tratamiento inicial)."))
        if not self.oir_b1_1571_signed:
            alerts.append(("warn", "Falta el OIR-B1-1571 firmado."))
        if not self.assignment_of_benefits_signed:
            alerts.append(("warn", "Falta la cesión de beneficios firmada."))
        if not self.emc_determined:
            alerts.append(("info", "EMC sin determinar: tope PIP de $2,500 hasta determinarla ($10,000 con EMC)."))
        return alerts

    def compliance_checklist(self):
        return [
            ("OIR-B1-1571 firmado", self.oir_b1_1571_signed),
            ("Cesión de beneficios firmada", self.assignment_of_benefits_signed),
            ("Declaración 5(e) firmada (puño y letra)", self.disclosure_5e_signed),
            ("EMC determinada", self.emc_determined),
            ("Notice of initiation enviado", bool(self.notice_of_initiation_date)),
        ]
