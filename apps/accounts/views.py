from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@require_POST
def ajax_login(request):
    """Login por AJAX para el modal de la portada.

    Devuelve JSON: {ok: true, redirect} o {ok: false, error}.
    Usa el mismo authenticate/login de Django, así la auditoría
    LoginAudit (señal user_logged_in) sigue funcionando.
    """
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    if not username or not password:
        return JsonResponse(
            {"ok": False, "error": "Escriba su usuario y contraseña."}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse(
            {"ok": False, "error": "Usuario o contraseña incorrectos."}, status=400)
    login(request, user)
    return JsonResponse({"ok": True, "redirect": "/inicio/"})


# ---------------- MFA (TOTP) ----------------
import base64
import io

import qrcode
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from . import mfa as mfa_lib
from .roles import get_role


def _qr_b64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _get_profile(request):
    prof = getattr(request.user, "profile", None)
    if prof is None:
        messages.error(request, "Su usuario no tiene perfil de clínica.")
        return None
    return prof


@login_required
def mfa_setup(request):
    """Alta del segundo factor: muestra el QR y activa al verificar el código."""
    prof = _get_profile(request)
    if prof is None:
        return redirect("dashboard")
    if prof.totp_enabled:
        messages.info(request, "El segundo factor ya está activado.")
        return redirect("dashboard")
    if request.method == "POST":
        secret = request.session.get("mfa_pending_secret", "")
        code = request.POST.get("code", "")
        if secret and mfa_lib.verify_code(secret, code):
            prof.totp_secret = mfa_lib.encrypt_secret(secret)
            prof.totp_enabled = True
            prof.totp_enabled_at = timezone.now()
            prof.save(update_fields=["totp_secret", "totp_enabled", "totp_enabled_at"])
            request.session["mfa_verified"] = True
            request.session.pop("mfa_pending_secret", None)
            messages.success(request, "Segundo factor activado correctamente.")
            return redirect("dashboard")
        messages.error(request, "Código incorrecto. Inténtelo de nuevo.")
    secret = mfa_lib.new_secret()
    request.session["mfa_pending_secret"] = secret
    uri = mfa_lib.provisioning_uri(
        secret, request.user.username,
        getattr(getattr(request, "tenant", None), "name", "clinica"))
    return render(request, "accounts/mfa_setup.html",
                  {"qr_b64": _qr_b64(uri), "manual_key": secret})


@login_required
def mfa_verify(request):
    """Segundo paso del inicio de sesión cuando el MFA está activado."""
    prof = _get_profile(request)
    if prof is None:
        return redirect("dashboard")
    if not prof.totp_enabled:
        return redirect("dashboard")
    if request.session.get("mfa_verified"):
        return redirect("dashboard")
    if request.method == "POST":
        secret = mfa_lib.decrypt_secret(prof.totp_secret)
        if mfa_lib.verify_code(secret, request.POST.get("code", "")):
            request.session["mfa_verified"] = True
            return redirect(request.GET.get("next") or "dashboard")
        messages.error(request, "Código incorrecto.")
    return render(request, "accounts/mfa_verify.html")


@login_required
def mfa_disable(request):
    """Desactiva el MFA (solo con la contraseña actual; no para admins)."""
    if request.method == "POST":
        if get_role(request.user) == "admin":
            messages.error(request, "Los administradores no pueden desactivar el segundo factor.")
            return redirect("dashboard")
        pwd = request.POST.get("password", "")
        user = authenticate(request, username=request.user.username, password=pwd)
        if user is None:
            messages.error(request, "Contraseña incorrecta.")
            return redirect("dashboard")
        prof = _get_profile(request)
        if prof is None:
            return redirect("dashboard")
        prof.totp_secret = ""
        prof.totp_enabled = False
        prof.totp_enabled_at = None
        prof.save(update_fields=["totp_secret", "totp_enabled", "totp_enabled_at"])
        request.session["mfa_verified"] = True
        messages.success(request, "Segundo factor desactivado.")
        return redirect("dashboard")
    return render(request, "accounts/mfa_disable.html")


# ---------------- Alertas de seguridad ----------------
from django.views.decorators.http import require_POST

from .models import SecurityAlert
from .roles import role_required


@require_POST
@role_required("admin")
def security_alert_review(request, pk):
    """Marca una alerta de seguridad como revisada."""
    alert = SecurityAlert.objects.filter(pk=pk, reviewed=False).first()
    if alert:
        alert.reviewed = True
        alert.reviewed_at = timezone.now()
        alert.save(update_fields=["reviewed", "reviewed_at"])
        messages.success(request, "Alerta marcada como revisada.")
    return redirect("dashboard")
