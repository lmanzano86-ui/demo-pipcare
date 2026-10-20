from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from patients.models import Accident

from .models import Appointment, STATUS_CHOICES
from .reminders import send_due_reminders


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["provider", "date", "start_time", "duration_min",
                  "appt_type", "status", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get("provider")
        d = cleaned.get("date")
        t = cleaned.get("start_time")
        dur = cleaned.get("duration_min") or 30
        if provider and d and t:
            start = t.hour * 60 + t.minute
            end = start + dur
            qs = Appointment.objects.filter(
                provider=provider, date=d).exclude(status="cancelled")
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            for a in qs:
                s2 = a.start_time.hour * 60 + a.start_time.minute
                e2 = s2 + a.duration_min
                if start < e2 and s2 < end:
                    raise forms.ValidationError(
                        f"{provider} ya tiene una cita de {a.start_time:%H:%M} a "
                        f"{a.end_time:%H:%M} ese día.")
        return cleaned


def _agenda_url(day):
    return f"{reverse('agenda')}?d={day.isoformat()}"


@login_required
def agenda(request):
    """Vista de día: citas ordenadas por hora, con navegación de fecha."""
    try:
        day = date.fromisoformat(request.GET.get("d", ""))
    except ValueError:
        day = date.today()
    appts = Appointment.objects.select_related(
        "accident__patient", "provider").filter(date=day).exclude(status="cancelled")
    counts = {s: 0 for s, _ in STATUS_CHOICES}
    for a in Appointment.objects.filter(date=day):
        counts[a.status] += 1
    return render(request, "scheduling/agenda.html", {
        "day": day,
        "prev_day": day - timedelta(days=1),
        "next_day": day + timedelta(days=1),
        "today": date.today(),
        "appointments": appts,
        "counts": counts,
        "is_today": day == date.today(),
    })


@login_required
def appointment_create(request, accident_pk=None):
    accident = None
    if accident_pk:
        accident = get_object_or_404(Accident, pk=accident_pk)
    elif request.GET.get("accident"):
        accident = get_object_or_404(Accident, pk=request.GET["accident"])
    q = request.GET.get("q", "").strip()
    results = []
    if q and not accident:
        results = Accident.objects.select_related("patient").filter(
            Q(patient__first_name__icontains=q) | Q(patient__last_name__icontains=q) |
            Q(patient__phone__icontains=q) | Q(claim_number__icontains=q)
        ).order_by("-date")[:10]

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        acc_id = request.POST.get("accident_id")
        accident = get_object_or_404(Accident, pk=acc_id) if acc_id else None
        if not accident:
            messages.error(request, "Seleccione el caso (paciente) para la cita.")
        elif form.is_valid():
            appt = form.save(commit=False)
            appt.accident = accident
            appt.save()
            messages.success(request, f"Cita agendada: {appt.date} {appt.start_time:%H:%M}.")
            return redirect(_agenda_url(appt.date))
    else:
        initial = {"provider": request.user.pk,
                   "date": request.GET.get("d", date.today().isoformat())}
        form = AppointmentForm(initial=initial)

    form.fields["provider"].queryset = User.objects.filter(
        is_active=True).order_by("first_name", "username")
    return render(request, "scheduling/appointment_form.html", {
        "form": form, "accident": accident, "q": q, "results": results,
        "title": "Nueva cita",
    })


@login_required
def appointment_update(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == "POST":
        form = AppointmentForm(request.POST, instance=appt)
        if form.is_valid():
            form.save()
            messages.success(request, "Cita actualizada.")
            return redirect(_agenda_url(appt.date))
    else:
        form = AppointmentForm(instance=appt)
    form.fields["provider"].queryset = User.objects.filter(
        is_active=True).order_by("first_name", "username")
    return render(request, "scheduling/appointment_form.html", {
        "form": form, "accident": appt.accident, "title": f"Editar cita del {appt.date}",
    })


@login_required
@require_POST
def appointment_set_status(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    new_status = request.POST.get("status")
    if new_status in dict(STATUS_CHOICES):
        appt.status = new_status
        appt.save(update_fields=["status"])
        messages.success(request, f"Cita marcada como: {appt.get_status_display()}.")
    return redirect(_agenda_url(appt.date))


@login_required
@require_POST
def reminders_now(request):
    """Envía ahora los recordatorios de las citas de mañana (sin esperar al cron)."""
    results = send_due_reminders(request.tenant)
    sent = sum(1 for _, ok, _ in results if ok)
    skipped = len(results) - sent
    messages.success(request, f"Recordatorios: {sent} enviados, {skipped} omitidos.")
    return render(request, "scheduling/reminders_result.html", {"results": results})
