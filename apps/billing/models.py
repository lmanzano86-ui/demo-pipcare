from django.db import models
from simple_history.models import HistoricalRecords
from clinical.models import Visit


class Claim(models.Model):
    """Reclamo (equivale a un CMS-1500): agrupa líneas de servicio por accidente."""

    STATUS_CHOICES = [
        ("draft", "Borrador"),
        ("ready", "Listo para enviar"),
        ("sent", "Enviado"),
        ("transmitted", "Transmitido electrónicamente (837P)"),
        ("paid", "Pagado"),
        ("partial", "Pago parcial"),
        ("denied", "Denegado"),
    ]

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="claims")
    status = models.CharField("estado", max_length=20, choices=STATUS_CHOICES, default="draft")
    payer = models.CharField("pagador (aseguradora)", max_length=150, blank=True)
    payer_id = models.CharField("ID del pagador (clearinghouse)", max_length=30, blank=True,
                                help_text="Identificador del pagador ante el clearinghouse (ej. 13333).")
    sent_at = models.DateTimeField("enviado el", null=True, blank=True)
    # FL 627.736(10): carta de demanda pre-demanda. Debe titularse
    # "demand letter under s. 627.736" y enviarse por correo certificado con
    # acuse de recibo a la dirección designada ante la OIR.
    demand_letter_sent = models.DateField("carta de demanda enviada el", null=True, blank=True)
    demand_letter_tracking = models.CharField("tracking del envío certificado", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    @property
    def total(self):
        return sum(line.charge for line in self.lines.all())

    def __str__(self):
        return f"Reclamo #{self.id} — {self.visit} (${self.total})"

    def cms1500_checklist(self):
        """Validación 'en su totalidad' del CMS-1500 (FL 627.736(5)(d)):
        el insurer no tiene aviso del monto salvo que el bill cumpla sustancialmente."""
        lines = list(self.lines.all())
        checks = [
            ("Pagador indicado", bool(self.payer)),
            ("Al menos una línea de servicio", bool(lines)),
            ("Todas las líneas tienen CPT/HCPCS", all(l.cpt_code for l in lines) if lines else False),
            ("Todas las líneas tienen ICD-10 y puntero diagnóstico",
             all(l.icd10_code and l.diagnosis_pointer for l in lines) if lines else False),
            ("Nota SOAP de la visita (base de necesidad médica)",
             hasattr(self.visit, "soap")),
        ]
        return checks

    def cms1500_ready(self):
        return all(ok for _, ok in self.cms1500_checklist())

    def coding_warnings(self):
        """Advertencias de codificación (NCCI / anti-upcoding, FL 627.736(5)(b))."""
        warnings = []
        for line in self.lines.all():
            warnings.extend(line.coding_warnings())
        return warnings


class ClaimLine(models.Model):
    """Una línea del CMS-1500: procedimiento + diagnóstico + modificadores."""

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="lines")
    date_of_service = models.DateField("fecha de servicio")
    cpt_code = models.CharField("CPT/HCPCS", max_length=10)  # ej. 98941
    modifier_1 = models.CharField("modificador 1", max_length=5, blank=True)  # ej. AT
    modifier_2 = models.CharField("modificador 2", max_length=5, blank=True)
    diagnosis_pointer = models.CharField("puntero diagnóstico", max_length=10, blank=True)  # ej. A,B
    icd10_code = models.CharField("ICD-10", max_length=10)  # ej. S13.4XXA
    units = models.PositiveIntegerField("unidades", default=1)
    charge = models.DecimalField("cargo", max_digits=10, decimal_places=2)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.cpt_code} x{self.units} — ${self.charge}"

    # Códigos de manipulación quiropráctica: AT = tratamiento activo.
    # Sin AT el pagador lo deniega como cuidado de mantenimiento.
    CHIRO_CODES = {"98940", "98941", "98942"}
    # Códigos E/M: el modificador 59 nunca aplica (usar 25 o XE/XP/XS/XU).
    EM_CODES = {"99202", "99203", "99204", "99205",
                "99211", "99212", "99213", "99214", "99215"}

    def coding_warnings(self):
        """Advertencias de codificación según NCCI y FL 627.736(5)(b) anti-upcoding."""
        w = []
        mods = {m.upper() for m in (self.modifier_1, self.modifier_2) if m}
        if self.cpt_code in self.CHIRO_CODES and "AT" not in mods:
            w.append(f"{self.cpt_code}: falta el modificador AT (tratamiento activo); "
                     "sin AT se deniega como mantenimiento.")
        if self.cpt_code in self.EM_CODES and "59" in mods:
            w.append(f"{self.cpt_code}: el modificador 59 nunca aplica a E/M; "
                     "usar 25 (o XE/XP/XS/XU) según el caso.")
        if not self.icd10_code:
            w.append(f"{self.cpt_code}: falta el código ICD-10 (diagnóstico).")
        if not self.diagnosis_pointer:
            w.append(f"{self.cpt_code}: falta el puntero diagnóstico (casillero 24E del CMS-1500).")
        return w


class Payment(models.Model):
    """Pagos conciliados del EOB."""

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField("monto", max_digits=10, decimal_places=2)
    date = models.DateField("fecha")
    eob_reference = models.CharField("referencia EOB", max_length=50, blank=True)
    notes = models.TextField("notas", blank=True)

    def __str__(self):
        return f"Pago ${self.amount} — {self.date}"


class Denial(models.Model):
    """Denegación y su apelación."""

    STATUS_CHOICES = [
        ("open", "Abierta"),
        ("appealed", "Apelada"),
        ("resolved", "Resuelta"),
        ("written_off", "Castigada"),
    ]

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="denials")
    code = models.CharField("código de denegación", max_length=20)
    reason = models.TextField("motivo")
    status = models.CharField("estado", max_length=20, choices=STATUS_CHOICES, default="open")
    appealed_at = models.DateTimeField("apelada el", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Denegación {self.code} — {self.claim}"


class EDITransmission(models.Model):
    """Archivo 837P generado para un reclamo y su estado de transmisión.

    El envío real al clearinghouse requiere contrato de la clínica (credenciales
    SFTP). Sin credenciales, el archivo queda en "generado" para subirlo manual
    al portal del clearinghouse.
    """
    STATUS_CHOICES = [
        ("generated", "Generado (pendiente de envío)"),
        ("sent", "Enviado al clearinghouse"),
        ("acknowledged", "Acuse recibido (999/277)"),
        ("failed", "Falló el envío"),
    ]

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="transmissions")
    file_name = models.CharField("archivo", max_length=100)
    content = models.TextField("contenido X12")
    control_number = models.CharField("nº de control", max_length=20)
    status = models.CharField("estado", max_length=20, choices=STATUS_CHOICES, default="generated")
    notes = models.TextField("notas", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField("enviado el", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} — {self.get_status_display()}"


class Service(models.Model):
    """Catálogo de servicios de la clínica (idea de Clinexa: Treatment).

    Define una vez cada servicio con su CPT, modificadores, ICD-10 y cargo
    por defecto; al facturar se agrega la línea al reclamo en un clic, sin
    teclear códigos. La línea creada sigue siendo editable.
    """
    CATEGORY_CHOICES = [
        ("visita", "Visita / Evaluación"),
        ("quiro", "Quiropráctico"),
        ("terapia", "Terapia / Rehabilitación"),
        ("examen", "Examen / Estudio"),
        ("otro", "Otro"),
    ]
    code = models.CharField("código interno", max_length=20, unique=True)
    name = models.CharField("servicio", max_length=120)
    category = models.CharField("categoría", max_length=20, choices=CATEGORY_CHOICES,
                                default="visita")
    default_cpt = models.CharField("CPT/HCPCS por defecto", max_length=10)
    default_modifier_1 = models.CharField("modificador 1", max_length=5, blank=True)
    default_modifier_2 = models.CharField("modificador 2", max_length=5, blank=True)
    default_icd10 = models.CharField("ICD-10 por defecto", max_length=10, blank=True)
    default_diagnosis_pointer = models.CharField("puntero diagnóstico", max_length=10,
                                                 blank=True)
    default_units = models.PositiveIntegerField("unidades por defecto", default=1)
    default_charge = models.DecimalField("cargo por defecto", max_digits=10,
                                         decimal_places=2)
    duration_min = models.PositiveIntegerField("duración (min)", default=30)
    is_active = models.BooleanField("activo", default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.code} — {self.name} ({self.default_cpt})"

    def to_claim_line(self, claim, date_of_service):
        """Crea la línea del reclamo con los valores por defecto."""
        return ClaimLine.objects.create(
            claim=claim, date_of_service=date_of_service,
            cpt_code=self.default_cpt, modifier_1=self.default_modifier_1,
            modifier_2=self.default_modifier_2,
            diagnosis_pointer=self.default_diagnosis_pointer,
            icd10_code=self.default_icd10, units=self.default_units,
            charge=self.default_charge,
        )
