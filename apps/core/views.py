"""Vistas del núcleo: cumplimiento (solo administradores)."""
from django.shortcuts import render

from accounts.roles import role_required

# Documentos de cumplimiento (carpeta "Risk Assessment" en Drive).
# Solo visibles para administradores de la clínica.
COMPLIANCE_DOCS = [
    {
        "title": "HIPAA Risk Assessment v1.2",
        "desc": "Análisis de riesgos de seguridad (metodología HHS/NIST): 15 riesgos evaluados, 0 altos, 1 medio, 14 bajos, con plan de remediación.",
        "url": "https://drive.google.com/file/d/1at8EosI946_JsVteVBWtEnjhCMcMMil6/view",
    },
    {
        "title": "Plan de Respuesta a Incidentes v1.0",
        "desc": "5 fases de respuesta, niveles de severidad, plazos legales (FIPA ≤30 días, HIPAA ≤60 días) y simulacro tabletop #1.",
        "url": "https://drive.google.com/file/d/1p5TiBcKjus3l2QjpsLwYFHIc-3dYmj3U/view",
    },
    {
        "title": "Checklist de Despliegue a Producción",
        "desc": "Requisitos antes del primer PHI real: RDS cifrado, secretos, cron de respaldos, BAA de AWS y Twilio.",
        "url": "https://drive.google.com/file/d/1zjt_UCQq3qkfMUMIu0dkcTwY7lZsye-l/view",
    },
    {
        "title": "Política de Accesos y Sanciones v1.0",
        "desc": "Roles y permisos, altas/bajas, revisión trimestral y tabla de sanciones.",
        "url": "https://drive.google.com/file/d/1JBAMkGnQjeEr1GMPWTys7sDUa_a5_0ae/view",
    },
    {
        "title": "Capacitación HIPAA del Personal",
        "desc": "Material de 45 minutos (5 módulos) + plantilla de registro de asistencia.",
        "url": "https://drive.google.com/file/d/1tr38lEG_OtnWPSBvzoZCxZoSDdziaW0I/view",
    },
    {
        "title": "Checklist Legal de Distribución",
        "desc": "Requisitos y costos para comercializar el sistema en Florida, en 3 fases.",
        "url": "https://drive.google.com/file/d/12YY0A0D5nj31WLYdkOxchc1VG_kTdKlf/view",
    },
]


@role_required("admin")
def compliance_docs(request):
    """Documentos de cumplimiento y seguridad (solo administradores)."""
    return render(request, "core/compliance.html", {"docs": COMPLIANCE_DOCS})
