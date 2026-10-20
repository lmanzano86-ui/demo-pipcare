from django import forms
from .models import Patient, Accident


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ["first_name", "last_name", "date_of_birth", "gender", "phone", "email", "address",
                  "emergency_contact_name", "emergency_contact_phone", "allergies",
                  "sms_consent", "self_pay"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {
            # TCPA: el consentimiento cubre recordatorios de salud, nunca marketing.
            "sms_consent": "El paciente acepta recibir recordatorios de citas por SMS (salud, no marketing).",
            # No Surprises Act: sin seguro => Good Faith Estimate obligatoria.
            "self_pay": "Sin seguro / paga de su bolsillo: requiere Good Faith Estimate por escrito.",
        }


class AccidentForm(forms.ModelForm):
    class Meta:
        model = Accident
        fields = ["date", "accident_type", "description", "claim_number",
                  "auto_insurer", "policy_number", "attorney",
                  "oir_b1_1571_signed", "assignment_of_benefits_signed",
                  "disclosure_5e_signed", "disclosure_5e_date",
                  "emc_determined", "emc_date", "notice_of_initiation_date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "disclosure_5e_date": forms.DateInput(attrs={"type": "date"}),
            "emc_date": forms.DateInput(attrs={"type": "date"}),
            "notice_of_initiation_date": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            # FL 627.736(5)(e): firma de puño y letra, original al insurer.
            "disclosure_5e_signed": "Debe firmarse DE PUÑO Y LETRA; el original se entrega a la aseguradora (no electrónico).",
            "emc_determined": "Determinada por MD/DO/PA/APRN: tope PIP $10,000. Sin EMC: $2,500.",
            "notice_of_initiation_date": "Enviar dentro de 21 días del primer tratamiento extiende timely filing a 75 días.",
        }
