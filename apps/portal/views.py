from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from documents.content import build_content
from documents.models import DOC_TYPES, ESIGN_TYPES, Document, DocTemplate, Signature, sync_accident_doc_flags
from patients.models import Patient
from scheduling.models import Appointment

from .models import PortalToken


def _token_or_404(token_str):
    """Valida el token del portal y devuelve (token, patient)."""
    t = get_object_or_404(PortalToken, token=token_str)
    if not t.is_valid():
        raise Http404("Enlace inválido o vencido.")
    t.last_used_at = timezone.now()
    t.save(update_fields=["last_used_at"])
    return t


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


# ---------- Vistas del paciente (sin login, con token) ----------

def home(request, token):
    t = _token_or_404(token)
    patient = t.patient
    accidents = patient.accidents.order_by("-date")[:10]
    upcoming = Appointment.objects.filter(
        accident__patient=patient, date__gte=date.today()
    ).exclude(status__in=("cancelled", "completed", "no_show")
              ).order_by("date", "start_time")[:5]
    pending_docs = 0
    for acc in accidents:
        signed = set(acc.documents.filter(status="firmado").values_list("doc_type", flat=True))
        pending_docs += len([dt for dt in ESIGN_TYPES if dt not in signed])
    return render(request, "portal/home.html", {
        "portal_token": t, "patient": patient, "accidents": accidents,
        "upcoming": upcoming, "pending_docs": pending_docs,
        "clinic": request.tenant,
    })


def documents(request, token):
    t = _token_or_404(token)
    patient = t.patient
    cases = []
    for acc in patient.accidents.order_by("-date"):
        signed = set(acc.documents.filter(status="firmado").values_list("doc_type", flat=True))
        items = [(dt, DOC_TYPES[dt], dt in signed) for dt in ESIGN_TYPES]
        cases.append((acc, items))
    return render(request, "portal/documents.html", {
        "portal_token": t, "patient": patient, "cases": cases, "clinic": request.tenant,
    })


def new_document(request, token, doc_type, accident_pk):
    t = _token_or_404(token)
    if doc_type not in ESIGN_TYPES:
        raise Http404("Documento no disponible en el portal.")
    accident = get_object_or_404(t.patient.accidents, pk=accident_pk)
    doc = Document.objects.create(doc_type=doc_type, accident=accident,
                                  template=DocTemplate.get_active(doc_type))
    return redirect("portal_sign", token=t.token, pk=doc.pk)


def sign(request, token, pk):
    t = _token_or_404(token)
    doc = get_object_or_404(Document, pk=pk, accident__patient=t.patient)
    if not doc.allows_esign:
        raise Http404("Documento no disponible en el portal.")
    if hasattr(doc, "esignature") and doc.esignature:
        return redirect("portal_documents", token=t.token)
    doc._clinic = request.tenant
    content = build_content(doc)
    cfg = doc.type_cfg
    patient = t.patient
    saved_signature = patient.signature_image or ""

    if request.method == "POST":
        signer_name = request.POST.get("signer_name", "").strip()
        use_saved = request.POST.get("use_saved") == "1" and saved_signature
        image_data = saved_signature if use_saved else request.POST.get("signature_data", "").strip()
        if not signer_name:
            messages.error(request, "Escriba el nombre del firmante.")
        elif not image_data.startswith("data:image/png;base64,") or len(image_data) < 1000:
            messages.error(request, "Debe dibujar su firma en el recuadro o usar la firma guardada.")
        else:
            Signature.objects.create(
                document=doc, signer_name=signer_name,
                signer_role=cfg["signer_role"], image_data=image_data,
                ip_address=_client_ip(request))
            if not use_saved:
                patient.signature_image = image_data
                patient.signature_saved_at = timezone.now()
                patient.save(update_fields=["signature_image", "signature_saved_at"])
            doc.status = "firmado"
            doc.completed_at = timezone.now()
            doc.save()
            sync_accident_doc_flags(doc.accident)
            messages.success(request, f"{cfg['name']} firmado. ¡Gracias!")
            return redirect("portal_documents", token=t.token)

    return render(request, "portal/sign.html", {
        "portal_token": t, "doc": doc, "content": content, "cfg": cfg,
        "saved_signature": saved_signature, "patient_name": str(patient),
        "clinic": request.tenant,
    })


def appointments(request, token):
    t = _token_or_404(token)
    upcoming = Appointment.objects.filter(
        accident__patient=t.patient, date__gte=date.today()
    ).exclude(status="cancelled").order_by("date", "start_time")[:20]
    return render(request, "portal/appointments.html", {
        "portal_token": t, "patient": t.patient, "upcoming": upcoming,
        "clinic": request.tenant,
    })


# ---------- Lado de la clínica (requiere login) ----------

@login_required
@require_POST
def token_create(request, patient_pk):
    patient = get_object_or_404(Patient, pk=patient_pk)
    patient.portal_tokens.filter(active=True).update(active=False)
    t = PortalToken.objects.create(patient=patient)
    messages.success(request, f"Enlace del portal generado (vence el {t.expires_at:%d/%m/%Y}).")
    return redirect("patient_detail", pk=patient.pk)


@login_required
@require_POST
def token_revoke(request, patient_pk):
    patient = get_object_or_404(Patient, pk=patient_pk)
    patient.portal_tokens.filter(active=True).update(active=False)
    messages.success(request, "Enlace del portal revocado.")
    return redirect("patient_detail", pk=patient.pk)
