from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.roles import role_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from clinical.models import Visit
from .cms1500 import build_cms1500_pdf
from .edi837 import build_837p
from .forms import ClaimLineForm
from .models import Claim, ClaimLine, Payment, Service
from .models import Claim, EDITransmission

import io
import time


@login_required
def claim_create(request, visit_pk):
    visit = get_object_or_404(Visit, pk=visit_pk)
    claim = Claim.objects.create(visit=visit, payer=visit.accident.auto_insurer or "")
    # Copia los diagnósticos de la nota SOAP como líneas base si existen
    return redirect("claim_detail", pk=claim.pk)


@login_required
def claim_detail(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    services = Service.objects.filter(is_active=True).order_by("category", "name")
    return render(request, "billing/claim_detail.html",
                  {"claim": claim, "services": services})


@role_required('admin', 'billing', 'provider')
def claim_add_line(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    if request.method == "POST":
        form = ClaimLineForm(request.POST)
        if form.is_valid():
            line = form.save(commit=False)
            line.claim = claim
            line.save()
            return redirect("claim_detail", pk=claim.pk)
    else:
        form = ClaimLineForm()
    return render(request, "billing/claimline_form.html", {"form": form, "claim": claim})


@role_required('admin', 'billing')
def claim_mark_sent(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    # FL 627.736(5)(d): el insurer no tiene aviso del monto salvo que el bill
    # cumpla sustancialmente "en su totalidad". Bloquear envío incompleto.
    if not claim.cms1500_ready():
        return render(request, "billing/claim_detail.html", {
            "claim": claim,
            "send_blocked": True,
        })
    claim.status = "sent"
    claim.sent_at = timezone.now()
    claim.save()
    return redirect("claim_detail", pk=claim.pk)


@login_required
def claim_pdf(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    pdf = build_cms1500_pdf(claim, request.tenant)
    return FileResponse(io.BytesIO(pdf), as_attachment=True,
                        filename=f"CMS1500-reclamo-{claim.pk}.pdf",
                        content_type="application/pdf")


@login_required
def demand_letter(request, pk):
    """Carta de demanda pre-demanda — FL 627.736(10).

    Condición precedente para demandar al insurer. Debe titularse
    "demand letter under s. 627.736", itemizar montos/fechas/tipos de
    tratamiento, adjuntar copia del assignment, y enviarse por correo
    certificado con acuse de recibo a la dirección designada ante la OIR.
    El insurer tiene 30 días para pagar lo vencido + interés + 10% (máx $250).
    """
    claim = get_object_or_404(Claim, pk=pk)
    accident = claim.visit.accident
    if request.method == "POST":
        claim.demand_letter_sent = request.POST.get("sent_date") or timezone.now().date()
        claim.demand_letter_tracking = request.POST.get("tracking", "")
        claim.save()
        return redirect("claim_detail", pk=claim.pk)
    lines = claim.lines.all()
    itemized = [
        {"date": l.date_of_service, "cpt": l.cpt_code, "desc": "", "amount": l.charge}
        for l in lines
    ]
    return render(request, "billing/demand_letter.html", {
        "claim": claim,
        "accident": accident,
        "patient": accident.patient,
        "itemized": itemized,
        "total": claim.total,
        "today": timezone.now().date(),
    })


@role_required('admin', 'billing')
def reports(request):
    """Reportes de dinero: resumen, por aseguradora, por proveedor y AR aging."""
    from .reports import ar_aging, money_report
    period = request.GET.get("period", "all")
    if period not in ("all", "month", "quarter", "year", "custom"):
        period = "all"
    start_str = request.GET.get("start", "") if period == "custom" else ""
    end_str = request.GET.get("end", "") if period == "custom" else ""
    data = money_report(period=period, start_str=start_str, end_str=end_str)
    data["aging"] = ar_aging()
    return render(request, "billing/reports.html", data)


@role_required('admin', 'billing')
def claim_update_payer(request, pk):
    """Actualiza pagador e ID del pagador (necesario para el 837P)."""
    claim = get_object_or_404(Claim, pk=pk)
    if request.method == "POST":
        claim.payer = request.POST.get("payer", "").strip()[:150]
        claim.payer_id = request.POST.get("payer_id", "").strip()[:30]
        claim.save(update_fields=["payer", "payer_id"])
        messages.success(request, "Pagador actualizado.")
    return redirect("claim_detail", pk=pk)


@role_required('admin', 'billing')
def claim_transmit(request, pk):
    """Genera el archivo 837P del reclamo y lo deja listo para transmitir."""
    from django.http import HttpResponse
    claim = get_object_or_404(Claim, pk=pk)
    if request.method == "POST":
        if not claim.cms1500_ready():
            messages.error(request, "El reclamo no pasa el checklist del CMS-1500.")
            return redirect("claim_detail", pk=pk)
        ctrl = str(int(time.time()))[-9:]
        content = build_837p(claim, request.tenant, ctrl)
        fname = f"837P_claim{claim.pk}_{ctrl}.x12"
        EDITransmission.objects.create(
            claim=claim, file_name=fname, content=content, control_number=ctrl)
        if claim.status in ("draft", "ready", "sent"):
            claim.status = "transmitted"
            claim.save(update_fields=["status"])
        messages.success(request, f"Archivo 837P generado: {fname}.")
        return redirect("claim_detail", pk=pk)
    # GET: descarga directa del último archivo generado
    trans = claim.transmissions.first()
    if not trans:
        messages.error(request, "Primero genere el archivo 837P.")
        return redirect("claim_detail", pk=pk)
    resp = HttpResponse(trans.content, content_type="application/edi-x12")
    resp["Content-Disposition"] = f'attachment; filename="{trans.file_name}"'
    return resp


# ---------- Catálogo de servicios ----------

@role_required('admin', 'billing')
def service_list(request):
    services = Service.objects.all().order_by("category", "name")
    return render(request, "billing/service_list.html", {"services": services})


@role_required('admin', 'billing')
def service_edit(request, pk=None):
    service = get_object_or_404(Service, pk=pk) if pk else None
    if request.method == "POST":
        data = request.POST
        fields = {
            "code": data.get("code", "").strip().upper(),
            "name": data.get("name", "").strip(),
            "category": data.get("category", "visita"),
            "default_cpt": data.get("default_cpt", "").strip(),
            "default_modifier_1": data.get("default_modifier_1", "").strip().upper(),
            "default_modifier_2": data.get("default_modifier_2", "").strip().upper(),
            "default_icd10": data.get("default_icd10", "").strip().upper(),
            "default_diagnosis_pointer": data.get("default_diagnosis_pointer", "").strip().upper(),
            "default_units": int(data.get("default_units") or 1),
            "default_charge": data.get("default_charge") or 0,
            "duration_min": int(data.get("duration_min") or 30),
        }
        if not fields["code"] or not fields["name"] or not fields["default_cpt"]:
            messages.error(request, "Código, nombre y CPT son obligatorios.")
        else:
            if service:
                for k, v in fields.items():
                    setattr(service, k, v)
                service.save()
                messages.success(request, f"Servicio {service.code} actualizado.")
            else:
                service = Service.objects.create(**fields)
                messages.success(request, f"Servicio {service.code} creado.")
            return redirect("service_list")
    return render(request, "billing/service_form.html", {"service": service})


@role_required('admin', 'billing')
@require_POST
def service_toggle(request, pk):
    service = get_object_or_404(Service, pk=pk)
    service.is_active = not service.is_active
    service.save(update_fields=["is_active"])
    messages.success(request,
                     f"Servicio {service.code} {'activado' if service.is_active else 'desactivado'}.")
    return redirect("service_list")


@role_required('admin', 'billing', 'provider')
@require_POST
def claimline_from_service(request, pk):
    """Agrega una línea al reclamo desde el catálogo, en un clic."""
    claim = get_object_or_404(Claim, pk=pk)
    service = get_object_or_404(Service, pk=request.POST.get("service_id"),
                                is_active=True)
    date_of_service = request.POST.get("date_of_service") or timezone.now().date()
    line = service.to_claim_line(claim, date_of_service)
    warnings = line.coding_warnings()
    if warnings:
        messages.warning(request, "Línea agregada con advertencias: " + " ".join(warnings))
    else:
        messages.success(request, f"Línea agregada: {line}.")
    return redirect("claim_detail", pk=claim.pk)
