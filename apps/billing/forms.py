from django import forms
from .models import ClaimLine


class ClaimLineForm(forms.ModelForm):
    class Meta:
        model = ClaimLine
        fields = ["date_of_service", "cpt_code", "modifier_1", "modifier_2",
                  "diagnosis_pointer", "icd10_code", "units", "charge"]
        widgets = {"date_of_service": forms.DateInput(attrs={"type": "date"})}
