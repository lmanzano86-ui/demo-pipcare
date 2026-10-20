from django import forms
from .models import OutcomeMeasure, SoapNote, Visit


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ["date", "provider", "visit_type"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class SoapNoteForm(forms.ModelForm):
    class Meta:
        model = SoapNote
        fields = ["subjective", "objective", "assessment", "plan"]
        widgets = {f: forms.Textarea(attrs={"rows": 4}) for f in
                   ["subjective", "objective", "assessment", "plan"]}


class OutcomeMeasureForm(forms.ModelForm):
    class Meta:
        model = OutcomeMeasure
        fields = ["measure_type", "score", "date", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
