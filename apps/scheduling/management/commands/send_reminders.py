"""Envía los recordatorios SMS de las citas de mañana (todas las clínicas).

Uso:  python manage.py send_reminders
Para producción: programarlo con cron una vez al día (ej. 8:00 AM).
"""

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from core.models import Clinic
from scheduling.reminders import send_due_reminders


class Command(BaseCommand):
    help = "Envía recordatorios SMS de las citas de mañana en todas las clínicas."

    def handle(self, *args, **options):
        total_ok = total_fail = 0
        for clinic in Clinic.objects.exclude(schema_name="public"):
            with schema_context(clinic.schema_name):
                for appt, ok, detail in send_due_reminders(clinic):
                    if ok:
                        total_ok += 1
                    else:
                        total_fail += 1
                    self.stdout.write(f"[{clinic.schema_name}] {appt} -> {detail}")
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {total_ok} enviados, {total_fail} omitidos/fallidos."))
