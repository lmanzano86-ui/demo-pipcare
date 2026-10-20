from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from .forms import AccidentForm, PatientForm
from .models import Accident, Patient


@login_required
def dashboard(request):
    patients = Patient.objects.order_by("-created_at")[:20]
    stats = {
        "patients": Patient.objects.count(),
        "cases": Accident.objects.count(),
        "pending_docs": Accident.objects.filter(
            Q(oir_b1_1571_signed=False) | Q(assignment_of_benefits_signed=False)
        ).count(),
    }
    # Alertas de cumplimiento PIP: relojes y documentos por caso.
    pip_alerts = []
    for accident in Accident.objects.order_by("-date")[:50]:
        for level, text in accident.pip_alerts():
            if level in ("bad", "warn"):
                pip_alerts.append({"level": level, "text": text, "accident": accident})
                if len(pip_alerts) >= 10:
                    break
        if len(pip_alerts) >= 10:
            break
    # Tablero de pendientes: qué tiene cumplido y qué le falta a cada caso.
    # Etiquetas cortas para las insignias del tablero.
    SHORT = {
        "OIR-B1-1571 firmado": "OIR-B1-1571",
        "Cesión de beneficios firmada": "AOB",
        "Declaración 5(e) firmada (puño y letra)": "5(e) puño y letra",
        "EMC determinada": "EMC",
        "Notice of initiation enviado": "Aviso de inicio",
    }
    # Stat rápido sobre TODOS los casos (solo checklist, sin consultas extra).
    ok_count = 0
    for accident in Accident.objects.only(
            "oir_b1_1571_signed", "assignment_of_benefits_signed",
            "disclosure_5e_signed", "emc_determined",
            "notice_of_initiation_date").iterator():
        if all(ok for _, ok in accident.compliance_checklist()):
            ok_count += 1
    stats["ok_cases"] = ok_count
    # Detalle (con relojes PIP) para los 40 casos más recientes.
    pending_cases = []
    for accident in Accident.objects.select_related("patient").order_by("-date")[:40]:
        checklist = accident.compliance_checklist()
        done = sum(1 for _, ok in checklist if ok)
        missing = [SHORT.get(label, label) for label, ok in checklist if not ok]
        alerts = [(lvl, txt) for lvl, txt in accident.pip_alerts() if lvl in ("bad", "warn")]
        if missing or alerts:
            pending_cases.append({
                "accident": accident, "done": done, "total": len(checklist),
                "missing": missing, "alerts": alerts,
            })
    from accounts.models import SecurityAlert
    security_alerts = SecurityAlert.objects.filter(reviewed=False)[:5]
    return render(request, "patients/dashboard.html",
                  {"patients": patients, "stats": stats, "pip_alerts": pip_alerts,
                   "pending_cases": pending_cases,
                   "security_alerts": security_alerts})


@login_required
def intake(request):
    """Admisión digital: paciente + accidente en un solo paso."""
    if request.method == "POST":
        p_form = PatientForm(request.POST, prefix="p")
        a_form = AccidentForm(request.POST, prefix="a")
        if p_form.is_valid() and a_form.is_valid():
            patient = p_form.save()
            accident = a_form.save(commit=False)
            accident.patient = patient
            accident.save()
            return redirect("accident_detail", pk=accident.pk)
    else:
        p_form = PatientForm(prefix="p")
        a_form = AccidentForm(prefix="a")
    return render(request, "patients/intake.html", {"p_form": p_form, "a_form": a_form})


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    portal_token = patient.portal_tokens.filter(active=True).first()
    if portal_token and not portal_token.is_valid():
        portal_token = None
    return render(request, "patients/patient_detail.html",
                  {"patient": patient, "portal_token": portal_token})


@login_required
def accident_detail(request, pk):
    accident = get_object_or_404(Accident, pk=pk)
    return render(request, "patients/accident_detail.html", {"accident": accident})
