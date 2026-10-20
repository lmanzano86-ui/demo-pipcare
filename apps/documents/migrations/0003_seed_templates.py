"""Siembra la versión 1 de cada plantilla legal y la asigna a los
documentos existentes. Corre por schema (cada clínica tiene las suyas)."""

from django.db import migrations


def seed_templates(apps, schema_editor):
    DocTemplate = apps.get_model("documents", "DocTemplate")
    Document = apps.get_model("documents", "Document")
    # Import directo: el contenido por defecto es estable.
    from documents.seed_templates import DEFAULT_TEMPLATES
    for doc_type, tpl in DEFAULT_TEMPLATES.items():
        template, created = DocTemplate.objects.get_or_create(
            doc_type=doc_type, version=1,
            defaults={
                "title": tpl["title"],
                "subtitle_tpl": tpl["subtitle_tpl"],
                "body_tpl": tpl["body_tpl"],
                "signer_label": tpl["signer_label"],
                "legal_note": tpl["legal_note"],
                "is_active": True,
            },
        )
        if created:
            Document.objects.filter(doc_type=doc_type,
                                    template__isnull=True).update(template=template)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [("documents", "0002_alter_signature_options_signature_invalidated_at_and_more")]

    operations = [migrations.RunPython(seed_templates, noop)]
