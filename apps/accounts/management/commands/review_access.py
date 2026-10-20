"""Revisión periódica de accesos (HIPAA 164.308(a)(3), 164.308(a)(1) — R-09).

Lista por clínica: usuario, rol, activo, último acceso, MFA y alertas
(cuentas inactivas >90 días, administradores sin MFA, sin perfil).

Uso:  python manage.py review_access
Para producción: ejecutarlo cada trimestre y archivar la salida firmada.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context

from accounts.roles import get_role
from core.models import Clinic

INACTIVE_DAYS = 90


class Command(BaseCommand):
    help = "Revisión trimestral de cuentas de usuario por clínica."

    def handle(self, *args, **options):
        now = timezone.now()
        total_flags = 0
        for clinic in Clinic.objects.exclude(schema_name="public").order_by("name"):
            self.stdout.write(f"\n=== {clinic.name} ({clinic.schema_name}) ===")
            with schema_context(clinic.schema_name):
                users = User.objects.order_by("username")
                if not users.exists():
                    self.stdout.write("  (sin usuarios)")
                    continue
                for u in users:
                    prof = getattr(u, "profile", None)
                    role = get_role(u)
                    last = u.last_login.strftime("%Y-%m-%d") if u.last_login else "nunca"
                    mfa = "sí" if (prof and prof.totp_enabled) else "NO"
                    flags = []
                    if not u.is_active:
                        flags.append("cuenta desactivada")
                    if u.last_login and (now - u.last_login) > timedelta(days=INACTIVE_DAYS):
                        flags.append(f"inactivo >{INACTIVE_DAYS} días")
                    if role == "admin" and mfa == "NO":
                        flags.append("ADMIN SIN MFA")
                    if prof is None:
                        flags.append("sin perfil")
                    total_flags += len(flags)
                    mark = "  [!] " if flags else "  "
                    self.stdout.write(
                        f"{mark}{u.username:20} rol={role:10} activo={u.is_active!s:5} "
                        f"último={last} mfa={mfa}"
                        + (f"  <-- {'; '.join(flags)}" if flags else ""))
        self.stdout.write(f"\nRevisión completa. Alertas totales: {total_flags}.")
        self.stdout.write("Archivar esta salida firmada como evidencia trimestral.")
