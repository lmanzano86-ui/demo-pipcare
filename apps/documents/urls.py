from django.urls import path

from . import views

urlpatterns = [
    path("documentos/", views.hub, name="documents_hub"),
    path("documentos/caso/<int:accident_pk>/", views.hub, name="documents_hub_case"),
    path("documentos/nuevo/<str:doc_type>/caso/<int:accident_pk>/",
         views.new_document, name="document_new"),
    path("documentos/<int:pk>/firmar/", views.sign, name="document_sign"),
    path("documentos/<int:pk>/", views.detail, name="document_detail"),
    path("documentos/<int:pk>/imprimir/", views.print_view, name="document_print"),
    path("documentos/<int:pk>/marcar-impreso/", views.mark_printed, name="document_mark_printed"),
    path("documentos/firma/<int:pk>/invalidar/", views.signature_invalidate,
         name="signature_invalidate"),
    path("plantillas/", views.template_list, name="template_list"),
    path("plantillas/<str:doc_type>/", views.template_detail, name="template_detail"),
    path("plantillas/<str:doc_type>/nueva-version/", views.template_new_version,
         name="template_new_version"),
]
