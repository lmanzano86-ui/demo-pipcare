"""Agenda de citas + recordatorios SMS (TCPA).

El recordatorio solo se envía si el paciente dio su consentimiento
(Patient.sms_allowed(): consintió, no lo revocó y tiene teléfono).
"""

from datetime import datetime, time as dtime, timedelta

from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords

APPT_TYPE_CHOICES = [
    ("initial", "Evaluación inicial"),
    ("followup", "Seguimiento"),
    ("therapy", "Terapia"),
    ("reexam", "Re-evaluación"),
    ("other", "Otro"),
]

STATUS_CHOICES = [
    ("scheduled", "Programada"),
    ("confirmed", "Confirmada"),
    ("arrived", "En sala"),
    ("completed", "Completada"),
    ("no_show", "No asistió"),
    ("cancelled", "Cancelada"),
]

# Colores del calendario por proveedor (se asigna por id).
PROVIDER_COLORS = ["#0F766E", "#2563EB", "#7C3AED", "#DB2777", "#EA580C", "#65A30D"]


class Appointment(models.Model):
    accident = models.ForeignKey("patients.Accident", on_delete=models.CASCADE,
                                 related_name="appointments", verbose_name="caso")
    provider = models.ForeignKey(User, on_delete=models.PROTECT,
                                 related_name="appointments", verbose_name="proveedor")
    date = models.DateField("fecha")
    start_time = models.TimeField("hora de inicio")
    duration_min = models.PositiveIntegerField("duración (min)", default=30)
    appt_type = models.CharField("tipo", max_length=20, choices=APPT_TYPE_CHOICES,
                                 default="followup")
    status = models.CharField("estado", max_length=20, choices=STATUS_CHOICES,
                              default="scheduled")
    notes = models.TextField("notas", blank=True)
    reminder_sent_at = models.DateTimeField("recordatorio enviado el", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.date} {self.start_time:%H:%M} — {self.accident.patient} ({self.provider})"

    @property
    def patient(self):
        return self.accident.patient

    @property
    def end_time(self):
        dt = datetime.combine(self.date, self.start_time)
        return (dt + timedelta(minutes=self.duration_min)).time()

    @property
    def provider_color(self):
        return PROVIDER_COLORS[(self.provider_id or 0) % len(PROVIDER_COLORS)]

    @property
    def is_past(self):
        from django.utils import timezone
        return datetime.combine(self.date, self.start_time) < timezone.now().replace(tzinfo=None)


class ReminderLog(models.Model):
    """Registro de cada recordatorio (auditoría TCPA)."""
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE,
                                    related_name="reminders")
    to_phone = models.CharField("teléfono destino", max_length=30)
    message = models.TextField("mensaje")
    sent_at = models.DateTimeField(auto_now_add=True)
    ok = models.BooleanField("enviado", default=False)
    detail = models.CharField("detalle", max_length=200, blank=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Recordatorio {self.appointment} → {'OK' if self.ok else 'falló'}"
