from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import include, path

from accounts import views as accounts_views
from core import views as core_views


def landing(request):
    """Portada pública del sistema. Si ya entró, va a su panel."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


def terminos(request):
    return render(request, "terminos.html")


def privacidad(request):
    return render(request, "privacidad.html")


urlpatterns = [
    path(settings.ADMIN_PATH, admin.site.urls),
    path("accounts/ajax-login/", accounts_views.ajax_login, name="ajax_login"),
    path("cuenta/mfa/configurar/", accounts_views.mfa_setup, name="mfa_setup"),
    path("cuenta/mfa/verificar/", accounts_views.mfa_verify, name="mfa_verify"),
    path("cuenta/mfa/desactivar/", accounts_views.mfa_disable, name="mfa_disable"),
    path("cuenta/alerta/<int:pk>/revisar/", accounts_views.security_alert_review,
         name="security_alert_review"),
    path("cumplimiento/", core_views.compliance_docs, name="compliance_docs"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("terminos/", terminos, name="terminos"),
    path("privacidad/", privacidad, name="privacidad"),
    path("", landing, name="landing"),
    path("", include("patients.urls")),
    path("", include("clinical.urls")),
    path("", include("billing.urls")),
    path("", include("documents.urls")),
    path("", include("scheduling.urls")),
    path("", include("portal.urls")),
]
