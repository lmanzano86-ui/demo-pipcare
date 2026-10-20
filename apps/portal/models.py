"""Portal del paciente: acceso por enlace seguro (token), sin contraseña.

La clínica genera un enlace único por paciente; el paciente ve sus citas y
firma electrónicamente sus documentos desde casa. El token:
- es imposible de adivinar (256 bits),
- solo da acceso a ESE paciente,
- vence en 30 días,
- se puede revocar y regenerar.
"""

import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

TOKEN_DAYS = 30


def _new_token():
    return secrets.token_urlsafe(32)


class PortalToken(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE,
                                related_name="portal_tokens")
    token = models.CharField("token", max_length=64, unique=True, default=_new_token)
    active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField("vence el")
    last_used_at = models.DateTimeField("último acceso", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Portal de {self.patient} ({'activo' if self.is_valid() else 'inactivo'})"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=TOKEN_DAYS)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.active and timezone.now() < self.expires_at

    def portal_url(self, request=None):
        path = f"/portal/{self.token}/"
        if request:
            return request.build_absolute_uri(path)
        return path
