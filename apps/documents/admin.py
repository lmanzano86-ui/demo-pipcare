from django.contrib import admin

from .models import Document, Signature


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "accident", "status", "created_at", "completed_at")
    list_filter = ("doc_type", "status")


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ("signer_name", "signer_role", "document", "signed_at", "ip_address")
    readonly_fields = ("signed_at",)
