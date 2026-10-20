from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.roles import role_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from patients.models import Accident

from .content import build_content
from .models import (DOC_TYPES, ESIGN_TYPES, WETINK_TYPES, Document,
                     DocTemplate, Signature, sync_accident_doc_flags)


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


@login_required
def hub(request, accident_pk=None):
    """Sesión central de formularios: se elige el caso y se ven todos los
    formularios con su estado. Repetir un formulario = nuevo registro."""
    accidents = Accident.objects.select_related("patient").order_by("-date")[:50]
    accident = None
    q = request.GET.get("q", "").strip()
    results = []
    if accident_pk:
        accident = get_object_or_404(Accident, pk=accident_pk)
    elif request.GET.get("caso"):
        accident = get_object_or_404(Accident, pk=request.GET["caso"])
    elif q:
        # Búsqueda por varios criterios: nombre, teléfono, reclamo o póliza.
        results = Accident.objects.select_related("patient").filter(
            Q(patient__first_name__icontains=q) | Q(patient__last_name__icontains=q) |
            Q(patient__phone__icontains=q) | Q(claim_number__icontains=q) |
            Q(policy_number__icontains=q)
        ).order_by("-date")[:20]

    docs_by_type = {}
    if accident:
        for d in accident.documents.all():
            docs_by_type.setdefault(d.doc_type, []).append(d)

    sections = []
    for title, desc, types in [
        ("Firma electrónica en pantalla",
         "Se firman aquí mismo con el dedo o el mouse. Válidos bajo ESIGN/UETA.",
         ESIGN_TYPES),
        ("Solo puño y letra (imprimir)",
         "La ley exige firma manuscrita. Se imprimen precargados con los datos del paciente.",
         WETINK_TYPES),
    ]:
        items = [(t, DOC_TYPES[t], docs_by_type.get(t, [])) for t in types]
        sections.append((title, desc, items))
    return render(request, "documents/hub.html", {
        "accidents": accidents, "accident": accident, "sections": sections,
        "q": q, "results": results,
    })


@login_required
def new_document(request, doc_type, accident_pk):
    """Crea el registro del formulario para el caso y redirige a firmar o imprimir."""
    if doc_type not in DOC_TYPES:
        messages.error(request, "Tipo de documento inválido.")
        return redirect("documents_hub")
    accident = get_object_or_404(Accident, pk=accident_pk)
    doc = Document.objects.create(doc_type=doc_type, accident=accident,
                                  template=DocTemplate.get_active(doc_type))
    if DOC_TYPES[doc_type]["esign"]:
        return redirect("document_sign", pk=doc.pk)
    return redirect("document_print", pk=doc.pk)


@login_required
def sign(request, pk):
    """Firma electrónica en pantalla (canvas). Solo tipos con esign=True."""
    doc = get_object_or_404(Document, pk=pk)
    if not doc.allows_esign:
        messages.error(request, "Este documento REQUIERE firma de puño y letra. Imprímalo.")
        return redirect("document_print", pk=doc.pk)
    if doc.esignature:
        return redirect("document_detail", pk=doc.pk)

    doc._clinic = request.tenant
    content = build_content(doc)
    cfg = doc.type_cfg
    patient = doc.accident.patient
    saved_signature = patient.signature_image or ""

    if request.method == "POST":
        signer_name = request.POST.get("signer_name", "").strip()
        use_saved = request.POST.get("use_saved") == "1" and saved_signature
        if use_saved:
            image_data = saved_signature
        else:
            image_data = request.POST.get("signature_data", "").strip()
        if not signer_name:
            messages.error(request, "Escriba el nombre del firmante.")
        elif not image_data.startswith("data:image/png;base64,") or len(image_data) < 1000:
            messages.error(request, "Debe dibujar su firma en el recuadro o usar la firma guardada.")
        else:
            Signature.objects.create(
                document=doc, signer_name=signer_name,
                signer_role=cfg["signer_role"], image_data=image_data,
                ip_address=_client_ip(request),
            )
            if not use_saved:
                # El paciente dibujó una firma: el sistema la recuerda para
                # aplicarla en otros documentos sin dibujarla de nuevo.
                patient.signature_image = image_data
                patient.signature_saved_at = timezone.now()
                patient.save()
            doc.status = "firmado"
            doc.completed_at = timezone.now()
            doc.save()
            # Sincroniza los flags de cumplimiento del caso (firmas válidas).
            sync_accident_doc_flags(doc.accident)
            messages.success(request, f"{cfg['name']} firmado electrónicamente.")
            return redirect("document_detail", pk=doc.pk)

    return render(request, "documents/sign.html", {
        "doc": doc, "content": content, "cfg": cfg,
        "saved_signature": saved_signature,
        "patient_name": str(patient),
    })


@login_required
def detail(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    doc._clinic = request.tenant
    content = build_content(doc)
    return render(request, "documents/detail.html", {
        "doc": doc, "content": content, "cfg": doc.type_cfg,
    })


@login_required
def print_view(request, pk):
    """Formulario precargado listo para imprimir (puño y letra o reimpresión)."""
    doc = get_object_or_404(Document, pk=pk)
    doc._clinic = request.tenant
    content = build_content(doc)
    return render(request, "documents/print.html", {
        "doc": doc, "content": content, "cfg": doc.type_cfg,
    })


@login_required
@require_POST
def mark_printed(request, pk):
    """Marca un documento de puño y letra como impreso/firmado a mano."""
    doc = get_object_or_404(Document, pk=pk)
    doc.status = "impreso"
    doc.completed_at = timezone.now()
    doc.notes = (doc.notes + "\n" if doc.notes else "") + \
        f"Marcado como impreso/firmado a mano por {request.user.username}."
    doc.save()
    if doc.doc_type == "disclosure_5e":
        acc = doc.accident
        acc.disclosure_5e_signed = True
        acc.disclosure_5e_date = timezone.now().date()
        acc.save()
    elif doc.doc_type == "notice_initiation":
        acc = doc.accident
        if not acc.notice_of_initiation_date:
            acc.notice_of_initiation_date = timezone.now().date()
            acc.save()
    messages.success(request, f"{doc.type_cfg['name']} marcado como completado.")
    return redirect("document_detail", pk=doc.pk)


# ---------- Plantillas legales versionadas (solo admin) ----------

@role_required('admin')
def template_list(request):
    """Las 9 plantillas con su versión activa."""
    rows = []
    for doc_type in DOC_TYPES:
        active = DocTemplate.get_active(doc_type)
        count = DocTemplate.objects.filter(doc_type=doc_type).count()
        rows.append({"doc_type": doc_type, "cfg": DOC_TYPES[doc_type],
                     "active": active, "count": count})
    return render(request, "documents/template_list.html", {"rows": rows})


@role_required('admin')
def template_detail(request, doc_type):
    """Versión activa + historial de versiones de un tipo."""
    if doc_type not in DOC_TYPES:
        raise Http404("Tipo inválido.")
    versions = DocTemplate.objects.filter(doc_type=doc_type).order_by("-version")
    return render(request, "documents/template_detail.html", {
        "doc_type": doc_type, "cfg": DOC_TYPES[doc_type],
        "versions": versions, "active": versions.filter(is_active=True).first(),
    })


@role_required('admin')
def template_new_version(request, doc_type):
    """Crea la versión N+1 del texto legal (la anterior queda intacta)."""
    if doc_type not in DOC_TYPES:
        raise Http404("Tipo inválido.")
    active = DocTemplate.get_active(doc_type)
    if request.method == "POST":
        DocTemplate.create_version(
            doc_type, user=request.user,
            title=request.POST.get("title", "").strip() or active.title,
            subtitle_tpl=request.POST.get("subtitle_tpl", "").strip(),
            body_tpl=request.POST.get("body_tpl", "").strip(),
            signer_label=request.POST.get("signer_label", "").strip() or active.signer_label,
            legal_note=request.POST.get("legal_note", "").strip(),
        )
        messages.success(request,
                         f"Nueva versión de {DOC_TYPES[doc_type]['name']} publicada. "
                         "Los documentos ya firmados conservan su versión original.")
        return redirect("template_detail", doc_type=doc_type)
    return render(request, "documents/template_form.html", {
        "doc_type": doc_type, "cfg": DOC_TYPES[doc_type], "active": active,
    })


# ---------- Invalidación de firmas ----------

@role_required('admin', 'provider')
@require_POST
def signature_invalidate(request, pk):
    """Invalida una firma con motivo (nunca se borra). El documento vuelve
    a borrador y puede firmarse de nuevo."""
    sig = get_object_or_404(Signature, pk=pk, is_valid=True)
    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Debe indicar el motivo de la invalidación.")
        return redirect("document_detail", pk=sig.document.pk)
    sig.invalidate(reason)
    doc = sig.document
    doc.status = "borrador"
    doc.completed_at = None
    doc.notes = (doc.notes + "\n" if doc.notes else "") + \
        f"Firma invalidada por {request.user.username}: {reason}"
    doc.save()
    sync_accident_doc_flags(doc.accident)
    messages.success(request, "Firma invalidada. El documento volvió a borrador.")
    return redirect("document_detail", pk=doc.pk)
