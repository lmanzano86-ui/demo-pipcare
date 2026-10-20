"""Roles de usuario y control de acceso (principio HIPAA de mínimo necesario).

Los roles viven en Profile (admin / provider / frontdesk / billing).
Este módulo centraliza:
- get_role(user): rol efectivo (frontdesk por defecto si no hay perfil).
- role_required(*roles): decorador para vistas.
- user_role_ctx: context processor para ocultar opciones del menú.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def get_role(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return "admin"
    try:
        return user.profile.role
    except Exception:
        return "frontdesk"


def role_required(*roles):
    """Solo usuarios autenticados con uno de los roles dados."""
    def deco(view):
        @wraps(view)
        @login_required
        def inner(request, *args, **kwargs):
            if get_role(request.user) not in roles:
                raise PermissionDenied(
                    "Su rol (%s) no tiene permiso para esta acción." % get_role(request.user))
            return view(request, *args, **kwargs)
        return inner
    return deco


def user_role_ctx(request):
    return {"user_role": get_role(request.user) if hasattr(request, "user") else None}
