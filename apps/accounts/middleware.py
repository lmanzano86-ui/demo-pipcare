"""Middleware de MFA (HIPAA 164.312(d) — riesgo R-02).

- Si el usuario tiene MFA activado y la sesión no pasó el segundo factor,
  lo redirige a la verificación (en cada inicio de sesión).
- Los administradores están OBLIGADOS a activar el MFA: si no lo tienen,
  se les redirige a configurarlo antes de usar el sistema.
"""
from django.shortcuts import redirect
from django.urls import reverse

from .roles import get_role

EXEMPT_PREFIXES = (
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/ajax-login/",
    "/cuenta/mfa/",
    "/static/",
)


def _profile(user):
    return getattr(user, "profile", None)


class MFAEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            path = request.path
            if not any(path.startswith(p) for p in EXEMPT_PREFIXES):
                prof = _profile(user)
                enabled = bool(prof and prof.totp_enabled)
                if enabled and not request.session.get("mfa_verified"):
                    return redirect(reverse("mfa_verify"))
                if not enabled and get_role(user) == "admin":
                    # Admin sin MFA: alta obligatoria (excepto superusuarios
                    # sin perfil en schema público, ej. primer arranque).
                    if prof is not None or not user.is_superuser:
                        return redirect(reverse("mfa_setup"))
        return self.get_response(request)
