"""Transmite por SFTP los archivos 837P generados (todas las clínicas).

Configuración (variables de entorno):
  EDI_SFTP_HOST, EDI_SFTP_USER, EDI_SFTP_PASSWORD o EDI_SFTP_KEY,
  EDI_SFTP_PATH (carpeta remota, default: /inbound)

Sin credenciales: lista los pendientes e indica que se suban manualmente al
portal del clearinghouse. Uso: python manage.py transmit_edi
"""

import io
import os

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context

from billing.models import EDITransmission
from core.models import Clinic


def _sftp_put(host, user, password, key_path, remote_path, file_name, content):
    """Sube por SFTP usando paramiko si está instalado."""
    try:
        import paramiko
    except ImportError:
        return False, "paramiko no instalado (pip install paramiko)"
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {"hostname": host, "username": user, "timeout": 30}
        if key_path and os.path.exists(key_path):
            kwargs["key_filename"] = key_path
        elif password:
            kwargs["password"] = password
        else:
            return False, "sin password ni llave SFTP"
        client.connect(**kwargs)
        sftp = client.open_sftp()
        remote = remote_path.rstrip("/") + "/" + file_name
        sftp.putfo(io.BytesIO(content.encode()), remote)
        sftp.close()
        client.close()
        return True, f"subido a {remote}"
    except Exception as e:  # noqa: BLE001
        return False, f"SFTP error: {e}"


class Command(BaseCommand):
    help = "Transmite por SFTP los archivos 837P pendientes."

    def handle(self, *args, **options):
        host = os.environ.get("EDI_SFTP_HOST", "").strip()
        user = os.environ.get("EDI_SFTP_USER", "").strip()
        if not (host and user):
            self.stdout.write(self.style.WARNING(
                "Sin EDI_SFTP_HOST/EDI_SFTP_USER: no se transmite. "
                "Suba los archivos manualmente al portal del clearinghouse."))
        remote_path = os.environ.get("EDI_SFTP_PATH", "/inbound")
        password = os.environ.get("EDI_SFTP_PASSWORD", "")
        key_path = os.environ.get("EDI_SFTP_KEY", "")
        n_ok = n_fail = 0
        for clinic in Clinic.objects.exclude(schema_name="public"):
            with schema_context(clinic.schema_name):
                pending = EDITransmission.objects.filter(status="generated")
                for t in pending:
                    if host and user:
                        ok, detail = _sftp_put(
                            host, user, password, key_path, remote_path,
                            t.file_name, t.content)
                    else:
                        ok, detail = False, "pendiente de subida manual"
                    t.status = "sent" if ok else t.status
                    if ok:
                        t.sent_at = timezone.now()
                    t.notes = (t.notes + "\n" if t.notes else "") + detail
                    t.save()
                    n_ok += ok
                    n_fail += (not ok)
                    self.stdout.write(f"[{clinic.schema_name}] {t.file_name} -> {detail}")
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {n_ok} transmitidos, {n_fail} pendientes."))
