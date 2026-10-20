from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from patients.models import Accident
from .forms import OutcomeMeasureForm, SoapNoteForm, VisitForm
from .models import TreatmentPlan, Visit


@login_required
def visit_create(request, accident_pk):
    accident = get_object_or_404(Accident, pk=accident_pk)
    if request.method == "POST":
        form = VisitForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.accident = accident
            visit.save()
            return redirect("soap_note", visit_pk=visit.pk)
    else:
        form = VisitForm()
    return render(request, "clinical/visit_form.html", {"form": form, "accident": accident})


@login_required
def soap_note(request, visit_pk):
    visit = get_object_or_404(Visit, pk=visit_pk)
    note = getattr(visit, "soap", None)
    if request.method == "POST":
        form = SoapNoteForm(request.POST, instance=note)
        if form.is_valid():
            soap = form.save(commit=False)
            soap.visit = visit
            soap.save()
            return redirect("accident_detail", pk=visit.accident.pk)
    else:
        form = SoapNoteForm(instance=note)
    return render(request, "clinical/soap_form.html", {"form": form, "visit": visit})


@login_required
def outcome_create(request, accident_pk):
    accident = get_object_or_404(Accident, pk=accident_pk)
    if request.method == "POST":
        form = OutcomeMeasureForm(request.POST)
        if form.is_valid():
            outcome = form.save(commit=False)
            outcome.accident = accident
            outcome.save()
            return redirect("accident_detail", pk=accident.pk)
    else:
        form = OutcomeMeasureForm()
    return render(request, "clinical/outcome_form.html", {"form": form, "accident": accident})


# ---------- Plan de tratamiento ----------

@login_required
def plan_create(request, accident_pk):
    accident = get_object_or_404(Accident, pk=accident_pk)
    if request.method == "POST":
        plan = TreatmentPlan.objects.create(
            accident=accident,
            title=request.POST.get("title", "").strip() or "Plan de cuidado quiropráctico",
            frequency=request.POST.get("frequency", "").strip(),
            sessions_prescribed=int(request.POST.get("sessions_prescribed") or 0),
            start_date=request.POST.get("start_date") or timezone.now().date(),
            end_date=request.POST.get("end_date") or None,
            notes=request.POST.get("notes", "").strip(),
            created_by=request.user,
        )
        messages.success(request, f"Plan creado: {plan.sessions_prescribed} sesiones indicadas.")
        return redirect("accident_detail", pk=accident.pk)
    return render(request, "clinical/plan_form.html", {"accident": accident})


@login_required
@require_POST
def plan_add_session(request, pk):
    plan = get_object_or_404(TreatmentPlan, pk=pk)
    try:
        plan.add_session()
        messages.success(request,
                         f"Sesión registrada ({plan.sessions_completed}/{plan.sessions_prescribed}).")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("accident_detail", pk=plan.accident.pk)


@login_required
@require_POST
def plan_set_status(request, pk):
    plan = get_object_or_404(TreatmentPlan, pk=pk)
    status = request.POST.get("status")
    if status in ("activo", "suspendido", "completado"):
        plan.status = status
        plan.save(update_fields=["status"])
        messages.success(request, f"Plan {plan.get_status_display().lower()}.")
    return redirect("accident_detail", pk=plan.accident.pk)
