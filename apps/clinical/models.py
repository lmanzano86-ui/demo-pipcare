from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords
from patients.models import Accident


class Visit(models.Model):
    accident = models.ForeignKey(Accident, on_delete=models.CASCADE, related_name="visits")
    date = models.DateField("fecha")
    provider = models.ForeignKey(User, on_delete=models.PROTECT, related_name="visits",
                                 verbose_name="proveedor")
    visit_type = models.CharField("tipo", max_length=20, default="followup",
                                  choices=[("initial", "Evaluación inicial"),
                                           ("followup", "Seguimiento")])
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"Visita {self.date} — {self.accident.patient}"


class SoapNote(models.Model):
    """Nota clínica diaria: base legal de cada CPT cobrado."""

    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name="soap")
    subjective = models.TextField("subjetivo (síntomas, dolor 0-10)")
    objective = models.TextField("objetivo (hallazgos, ROM, palpación)")
    assessment = models.TextField("evaluación (diagnósticos)")
    plan = models.TextField("plan (frecuencia, próximos pasos)")

    def __str__(self):
        return f"SOAP {self.visit}"


class OutcomeMeasure(models.Model):
    """Mediciones funcionales: Oswestry, NDI, escala de dolor."""

    TYPE_CHOICES = [
        ("oswestry", "Oswestry (lumbar)"),
        ("ndi", "Neck Disability Index"),
        ("pain", "Escala de dolor 0-10"),
    ]

    accident = models.ForeignKey(Accident, on_delete=models.CASCADE, related_name="outcomes")
    measure_type = models.CharField("tipo", max_length=20, choices=TYPE_CHOICES)
    score = models.DecimalField("puntaje", max_digits=5, decimal_places=1)
    date = models.DateField("fecha")
    notes = models.TextField("notas", blank=True)

    def __str__(self):
        return f"{self.get_measure_type_display()} {self.score} — {self.date}"


class TreatmentPlan(models.Model):
    """Plan de tratamiento del caso (idea de Clinexa: PatientTreatment).

    El proveedor prescribe N sesiones con una frecuencia (ej. "12 sesiones,
    3x por semana"); el progreso se registra sesión por sesión. Documenta la
    necesidad médica del tratamiento, clave para PIP.
    """
    STATUS_CHOICES = [
        ("activo", "Activo"),
        ("completado", "Completado"),
        ("suspendido", "Suspendido"),
    ]
    accident = models.ForeignKey("patients.Accident", on_delete=models.CASCADE,
                                 related_name="treatment_plans", verbose_name="caso")
    title = models.CharField("plan", max_length=160,
                             default="Plan de cuidado quiropráctico")
    frequency = models.CharField("frecuencia", max_length=80, blank=True,
                                 help_text="Ej.: 3 veces por semana")
    sessions_prescribed = models.PositiveIntegerField("sesiones indicadas")
    sessions_completed = models.PositiveIntegerField("sesiones realizadas", default=0)
    status = models.CharField("estado", max_length=20, choices=STATUS_CHOICES,
                              default="activo")
    start_date = models.DateField("inicio")
    end_date = models.DateField("fin estimado", null=True, blank=True)
    notes = models.TextField("notas clínicas", blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True,
                                   on_delete=models.SET_NULL, verbose_name="indicado por")
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.sessions_completed}/{self.sessions_prescribed})"

    @property
    def progress_pct(self):
        if not self.sessions_prescribed:
            return 0
        return min(100, round(100 * self.sessions_completed / self.sessions_prescribed))

    def add_session(self):
        """Registra una sesión realizada; completa el plan al llegar a la meta."""
        if self.status != "activo":
            raise ValueError("El plan no está activo.")
        self.sessions_completed += 1
        if self.sessions_completed >= self.sessions_prescribed:
            self.status = "completado"
        self.save(update_fields=["sessions_completed", "status"])
