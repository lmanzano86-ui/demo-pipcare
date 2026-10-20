"""Documentos y formularios del caso: firma electrónica o puño y letra.

Base legal (investigación 18 oct 2026):
- ESIGN Act (federal) + UETA de Florida (F.S. 668.50): la firma electrónica es
  válida si hay intención, consentimiento, atribución y conservación. Aplica a:
  OIR-B1-1571, cesión de beneficios (AOB médica PIP), autorización HIPAA,
  consentimiento SMS (TCPA), consentimiento de tratamiento y acuse de GFE.
- FL 627.736(5)(e): la declaración y reconocimiento (disclosure) exige firma
  MANUSCRITA del profesional y el original se entrega a la aseguradora
  (NO electrónico). -> solo puño y letra, formulario imprimible precargado.
- FL 627.736(6)(b): declaración jurada (sworn statement) bajo juramento ->
  típicamente ante notario -> solo puño y letra.
- Aviso de inicio de tratamiento (5)(c): carta del proveedor, se envía por
  correo -> imprimible precargado.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

# doc_type -> configuración. "esign": True = se firma en pantalla (canvas);
# False = REQUIERE puño y letra -> solo se imprime precargado.
DOC_TYPES = {
    # --- Firma electrónica permitida (ESIGN / UETA FL 668.50) ---
    "aob": {
        "name": "Cesión de beneficios (AOB)",
        "esign": True, "signer_role": "patient",
        "desc": "El paciente cede a la clínica el cobro directo de sus beneficios PIP.",
    },
    "hipaa_auth": {
        "name": "Autorización HIPAA",
        "esign": True, "signer_role": "patient",
        "desc": "Autoriza a la clínica a usar/divulgar su información de salud (45 CFR 164.508).",
    },
    "tcpa_consent": {
        "name": "Consentimiento SMS (TCPA)",
        "esign": True, "signer_role": "patient",
        "desc": "Consiente recibir recordatorios de citas por SMS (solo salud, no marketing).",
    },
    "consent_treat": {
        "name": "Consentimiento de tratamiento",
        "esign": True, "signer_role": "patient",
        "desc": "Consentimiento informado para evaluación y tratamiento quiropráctico/médico.",
    },
    "oir_b1_1571": {
        "name": "OIR-B1-1571",
        "esign": True, "signer_role": "patient",
        "desc": "El asegurado afirma que los servicios PIP le fueron explicados y recibidos.",
    },
    "gfe_ack": {
        "name": "Acuse de Good Faith Estimate",
        "esign": True, "signer_role": "patient",
        "desc": "Paciente sin seguro / auto-pago: acusa recibo del estimado de buena fe (No Surprises Act).",
    },
    # --- SOLO puño y letra (imprimir precargado) ---
    "disclosure_5e": {
        "name": "Declaración 5(e) — puño y letra",
        "esign": False, "signer_role": "provider",
        "desc": "FL 627.736(5)(e): exige firma MANUSCRITA del profesional; el original va a la aseguradora (NO electrónico).",
    },
    "sworn_statement": {
        "name": "Declaración jurada (6)(b) — puño y letra",
        "esign": False, "signer_role": "patient",
        "desc": "Declaración bajo juramento; típicamente ante notario. Imprimir y firmar a mano.",
    },
    "notice_initiation": {
        "name": "Aviso de inicio de tratamiento",
        "esign": False, "signer_role": "provider",
        "desc": "Carta del proveedor a la aseguradora dentro de 21 días (extiende timely filing a 75 días).",
    },
}

ESIGN_TYPES = [k for k, v in DOC_TYPES.items() if v["esign"]]
WETINK_TYPES = [k for k, v in DOC_TYPES.items() if not v["esign"]]

STATUS_CHOICES = [
    ("borrador", "Borrador"),
    ("firmado", "Firmado electrónicamente"),
    ("impreso", "Impreso / firmado a mano"),
]


class DocTemplate(models.Model):
    """Texto legal versionado de un formulario (idea tomada de Clinexa).

    Cada tipo de documento tiene versiones INMUTABLES; solo una está activa.
    Editar el texto legal = crear una nueva versión (la anterior se conserva
    intacta). Cada Document guarda la plantilla con la que se generó, así cada
    firma queda atada a la versión exacta del texto que se firmó.
    """
    doc_type = models.CharField("tipo de documento", max_length=30,
                               choices=[(k, v["name"]) for k, v in DOC_TYPES.items()])
    version = models.PositiveIntegerField("versión")
    title = models.CharField("título", max_length=200)
    subtitle_tpl = models.CharField("subtítulo (plantilla)", max_length=300, blank=True)
    body_tpl = models.TextField("cuerpo HTML (plantilla con {placeholders})")
    signer_label = models.CharField("etiqueta del firmante", max_length=200)
    legal_note = models.CharField("nota legal", max_length=300, blank=True)
    is_active = models.BooleanField("activa", default=True)
    effective_date = models.DateField("vigente desde", auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, verbose_name="creada por")
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        unique_together = ("doc_type", "version")
        ordering = ("doc_type", "-version")

    def __str__(self):
        estado = "activa" if self.is_active else "histórica"
        return f"{self.get_doc_type_display()} v{self.version} ({estado})"

    def save(self, *args, **kwargs):
        # Inmutabilidad: una versión publicada jamás se edita.
        if self.pk:
            raise ValueError("Las plantillas son inmutables: cree una nueva versión.")
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls, doc_type):
        return cls.objects.filter(doc_type=doc_type, is_active=True).first()

    @classmethod
    def create_version(cls, doc_type, user=None, **fields):
        """Crea la versión N+1 y desactiva la anterior (operación atómica)."""
        current = cls.get_active(doc_type)
        version = (current.version + 1) if current else 1
        cls.objects.filter(doc_type=doc_type, is_active=True).update(is_active=False)
        return cls.objects.create(doc_type=doc_type, version=version,
                                  created_by=user, **fields)


class Document(models.Model):
    """Un formulario generado para un caso. Repetir = nuevo registro (auditoría)."""
    doc_type = models.CharField("tipo de documento", max_length=30,
                               choices=[(k, v["name"]) for k, v in DOC_TYPES.items()])
    accident = models.ForeignKey("patients.Accident", on_delete=models.CASCADE,
                                 related_name="documents", verbose_name="caso")
    template = models.ForeignKey(DocTemplate, null=True, blank=True,
                                 on_delete=models.PROTECT, related_name="documents",
                                 verbose_name="plantilla (versión del texto)")
    status = models.CharField("estado", max_length=20, choices=STATUS_CHOICES, default="borrador")
    notes = models.TextField("notas", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField("completado el", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.accident}"

    @property
    def type_cfg(self):
        return DOC_TYPES[self.doc_type]

    @property
    def allows_esign(self):
        return self.type_cfg["esign"]

    @property
    def esignature(self):
        """La firma válida vigente (None si no hay o fue invalidada)."""
        return self.signatures.filter(is_valid=True).order_by("-signed_at").first()


class Signature(models.Model):
    """Firma electrónica capturada en pantalla (canvas -> PNG base64).

    Validez ESIGN/UETA: intención (acto de dibujar + botón), consentimiento
    (texto ESIGN aceptado), atribución (nombre + IP + fecha/hora) y
    conservación (registro + historial inmutable).

    Una firma NUNCA se borra ni se edita: si pierde validez se INVALIDA con
    motivo (patrón de Clinexa), el documento vuelve a borrador y puede
    firmarse de nuevo (nuevo registro de firma).
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE,
                                 related_name="signatures")
    signer_name = models.CharField("nombre del firmante", max_length=200)
    signer_role = models.CharField("firma como", max_length=20,
                                   choices=[("patient", "Paciente"), ("provider", "Proveedor")])
    image_data = models.TextField("imagen de la firma (PNG base64)")
    method = models.CharField("método", max_length=20, default="electronic")
    consent_version = models.CharField("versión del consentimiento ESIGN", max_length=20, default="v1")
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    signed_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField("válida", default=True)
    invalidated_at = models.DateTimeField("invalidada el", null=True, blank=True)
    invalidation_reason = models.TextField("motivo de invalidación", blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-signed_at"]

    def __str__(self):
        estado = "" if self.is_valid else " (INVALIDADA)"
        return f"Firma de {self.signer_name} ({self.signed_at:%Y-%m-%d %H:%M}){estado}"

    def invalidate(self, reason):
        """Invalida la firma con motivo. No la borra: queda en auditoría."""
        if not self.is_valid:
            raise ValueError("La firma ya está invalidada.")
        self.is_valid = False
        self.invalidated_at = timezone.now()
        self.invalidation_reason = reason
        self.save(update_fields=["is_valid", "invalidated_at", "invalidation_reason"])


def sync_accident_doc_flags(accident):
    """Recalcula los flags de cumplimiento según las firmas VÁLIDAS vigentes."""
    accident.oir_b1_1571_signed = accident.documents.filter(
        doc_type="oir_b1_1571", status="firmado",
        signatures__is_valid=True).exists()
    accident.assignment_of_benefits_signed = accident.documents.filter(
        doc_type="aob", status="firmado",
        signatures__is_valid=True).exists()
    accident.save(update_fields=["oir_b1_1571_signed",
                                 "assignment_of_benefits_signed"])
