"""Contenido de los formularios legales.

Los textos viven como PLANTILLAS VERSIONADAS (DocTemplate): cada tipo tiene
versiones inmutables y solo una activa. Aquí está el render: toma la plantilla
(activa al crear el documento, o la v1 por defecto) y rellena los
{placeholders} con los datos del caso.

Los textos por defecto están en seed_templates.py (versión 1 de cada tipo).
"""

from django.utils.html import escape

from .seed_templates import DEFAULT_TEMPLATES


def template_context(document, accident, patient, clinic):
    """Valores para los {placeholders}, escapados y con '—' donde aplica."""
    p = lambda v: escape(str(v or ""))
    dash = lambda v: p(v) or "—"
    return {
        "patient_name": p(f"{patient.first_name} {patient.last_name}"),
        "patient_dob": p(patient.date_of_birth),
        "patient_phone": dash(patient.phone),
        "patient_address": dash(patient.address),
        "accident_date": p(accident.date),
        "claim_number": dash(accident.claim_number),
        "insurer": dash(accident.auto_insurer),
        "policy_number": dash(accident.policy_number),
        "clinic_name": p(getattr(clinic, "name", "")),
        "clinic_npi": dash(getattr(clinic, "npi", "")),
        "clinic_phone": dash(getattr(clinic, "phone", "")),
        "clinic_address": p(getattr(clinic, "address", "")),
    }


def render_dict(tpl, document):
    """Rellena un dict de plantilla (de DocTemplate o de DEFAULT_TEMPLATES)."""
    ctx = template_context(document, document.accident,
                           document.accident.patient,
                           getattr(document, "_clinic", None))
    return {
        "title": tpl["title"].format(**ctx),
        "subtitle": tpl["subtitle_tpl"].format(**ctx),
        "body_html": tpl["body_tpl"].format(**ctx),
        "signer_label": tpl["signer_label"],
        "legal_note": tpl["legal_note"],
    }


def build_content(document):
    """Contenido precargado del documento, según su plantilla versionada."""
    if getattr(document, "template_id", None):
        t = document.template
        tpl = {"title": t.title, "subtitle_tpl": t.subtitle_tpl,
               "body_tpl": t.body_tpl, "signer_label": t.signer_label,
               "legal_note": t.legal_note}
    else:
        # Documentos creados antes del versionado: texto v1 por defecto.
        tpl = DEFAULT_TEMPLATES[document.doc_type]
    return render_dict(tpl, document)
