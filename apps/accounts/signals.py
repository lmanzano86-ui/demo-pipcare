"""Señales de auditoría de accesos (HIPAA 164.312(b))."""
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from .models import LoginAudit


def _ip(request):
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def audit_login_ok(sender, request, user, **kwargs):
    LoginAudit.objects.create(user=user, ip_address=_ip(request), success=True)


FAIL_THRESHOLD = 5       # intentos
FAIL_WINDOW_MIN = 10       # minutos


@receiver(user_login_failed)
def audit_login_fail(sender, credentials, request, **kwargs):
    from django.contrib.auth.models import User
    from django.utils import timezone
    try:
        user = User.objects.get(username=credentials.get("username"))
    except User.DoesNotExist:
        return
    LoginAudit.objects.create(user=user, ip_address=_ip(request), success=False)
    # HIPAA R-11: ráfaga de fallos -> alerta (una sola vez al cruzar el umbral).
    since = timezone.now() - timezone.timedelta(minutes=FAIL_WINDOW_MIN)
    fails = LoginAudit.objects.filter(
        user=user, success=False, timestamp__gte=since).count()
    if fails == FAIL_THRESHOLD:
        from .models import SecurityAlert
        SecurityAlert.objects.create(
            kind="login_burst",
            title=f"Ráfaga de intentos fallidos: {user.username}",
            detail=(f"{fails} intentos fallidos en {FAIL_WINDOW_MIN} minutos "
                    f"(IP: {_ip(request)}). Verifique si es un ataque o un "
                    f"usuario con problemas; considere bloquear la cuenta."))
