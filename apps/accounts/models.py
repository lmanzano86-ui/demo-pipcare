from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords


class Profile(models.Model):
    """Rol del usuario dentro de su clínica (los usuarios viven por tenant)."""

    ROLE_CHOICES = [
        ("admin", "Administrador de clínica"),
        ("provider", "Proveedor (DC/MD)"),
        ("frontdesk", "Recepción"),
        ("billing", "Facturación"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField("rol", max_length=20, choices=ROLE_CHOICES, default="frontdesk")
    npi = models.CharField("NPI del proveedor", max_length=20, blank=True)
    active = models.BooleanField("activo", default=True)
    # MFA TOTP (HIPAA 164.312(d) — R-02). El secreto se guarda CIFRADO
    # con Fernet (ver accounts/mfa.py); el segundo factor se exige en cada
    # inicio de sesión una vez activado. Obligatorio para administradores.
    totp_secret = models.CharField("secreto TOTP (cifrado)", max_length=255, blank=True)
    totp_enabled = models.BooleanField("MFA activado", default=False)
    totp_enabled_at = models.DateTimeField("MFA activado el", null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class LoginAudit(models.Model):
    """Registro de accesos (HIPAA Security Rule: controles de auditoría 164.312(b)).

    Quién entró, cuándo y desde qué IP. Inmutable: sin edición ni borrado
    desde la interfaz.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_audits")
    timestamp = models.DateTimeField("fecha/hora", auto_now_add=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    success = models.BooleanField("exitoso", default=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} — {self.timestamp:%Y-%m-%d %H:%M} ({'OK' if self.success else 'FALLO'})"


class SecurityAlert(models.Model):
    """Alertas de seguridad (HIPAA R-11): p. ej. ráfaga de logins fallidos.

    Se generan automáticamente; un admin las marca como revisadas.
    """
    KIND_CHOICES = [
        ("login_burst", "Ráfaga de intentos fallidos"),
        ("other", "Otra"),
    ]
    kind = models.CharField("tipo", max_length=20, choices=KIND_CHOICES, default="other")
    title = models.CharField("título", max_length=200)
    detail = models.TextField("detalle", blank=True)
    created_at = models.DateTimeField("creada", auto_now_add=True)
    reviewed = models.BooleanField("revisada", default=False)
    reviewed_at = models.DateTimeField("revisada el", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{'OK' if self.reviewed else '!'}] {self.title}"
