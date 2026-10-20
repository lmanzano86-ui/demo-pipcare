from django.urls import path

from . import views

urlpatterns = [
    # Portal del paciente (token, sin login)
    path("portal/<str:token>/", views.home, name="portal_home"),
    path("portal/<str:token>/documentos/", views.documents, name="portal_documents"),
    path("portal/<str:token>/documentos/nuevo/<str:doc_type>/caso/<int:accident_pk>/",
         views.new_document, name="portal_new_document"),
    path("portal/<str:token>/firmar/<int:pk>/", views.sign, name="portal_sign"),
    path("portal/<str:token>/citas/", views.appointments, name="portal_appointments"),
    # Lado de la clínica
    path("paciente/<int:patient_pk>/portal/generar/", views.token_create,
         name="portal_token_create"),
    path("paciente/<int:patient_pk>/portal/revocar/", views.token_revoke,
         name="portal_token_revoke"),
]
