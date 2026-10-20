"""Lógica de recordatorios: citas de mañana, solo con consentimiento TCPA."""

from datetime import date, timedelta

from django.utils import timezone

from .models import Appointment, ReminderLog
from .sms import send_sms


def reminder_message(appointment, clinic):
    p = appointment.patient
    cname = getattr(clinic, "name", "la clínica")
    cphone = getattr(clinic, "phone", "") or ""
    return (
        f"Hola {p.first_name}, le recordamos su cita en {cname} "
        f"el {appointment.date:%d/%m/%Y} a las {appointment.start_time:%H:%M} "
        f"con {appointment.provider.get_full_name() or appointment.provider.username}."
        + (f" Llame al {cphone} si necesita reprogramar." if cphone else "")
        + " Responda STOP para no recibir más mensajes."
    )


def send_due_reminders(clinic):
    """Envía recordatorios de las citas de mañana. Devuelve lista de resultados."""
    tomorrow = date.today() + timedelta(days=1)
    results = []
    qs = Appointment.objects.select_related("accident__patient", "provider").filter(
        date=tomorrow,
        status__in=("scheduled", "confirmed"),
        reminder_sent_at__isnull=True,
    )
    from .sms import _twilio_cfg
    twilio_real = _twilio_cfg() is not None
    for appt in qs:
        patient = appt.patient
        if not patient.sms_allowed():
            results.append((appt, False, "omitido: sin consentimiento SMS válido"))
            continue
        # HIPAA R-06: con Twilio real se exige su BAA firmado (el SMS lleva ePHI).
        if twilio_real and not getattr(clinic, "twilio_baa_signed", False):
            results.append((appt, False, "omitido: falta el BAA firmado de Twilio"))
            continue
        msg = reminder_message(appt, clinic)
        ok, detail = send_sms(patient.phone, msg)
        ReminderLog.objects.create(
            appointment=appt, to_phone=patient.phone, message=msg, ok=ok, detail=detail)
        if ok:
            appt.reminder_sent_at = timezone.now()
            appt.save(update_fields=["reminder_sent_at"])
        results.append((appt, ok, detail))
    return results
