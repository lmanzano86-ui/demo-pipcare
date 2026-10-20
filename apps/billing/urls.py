from django.urls import path
from . import views

urlpatterns = [
    path("visita/<int:visit_pk>/reclamo/nuevo/", views.claim_create, name="claim_create"),
    path("reclamo/<int:pk>/", views.claim_detail, name="claim_detail"),
    path("reclamo/<int:pk>/linea/nueva/", views.claim_add_line, name="claim_add_line"),
    path("reclamo/<int:pk>/enviar/", views.claim_mark_sent, name="claim_mark_sent"),
    path("reclamo/<int:pk>/pdf/", views.claim_pdf, name="claim_pdf"),
    path("reclamo/<int:pk>/carta-demanda/", views.demand_letter, name="demand_letter"),
    path("reportes/", views.reports, name="reports"),
    path("reclamo/<int:pk>/pagador/", views.claim_update_payer, name="claim_update_payer"),
    path("reclamo/<int:pk>/837/", views.claim_transmit, name="claim_transmit"),
    path("servicios/", views.service_list, name="service_list"),
    path("servicios/nuevo/", views.service_edit, name="service_new"),
    path("servicios/<int:pk>/editar/", views.service_edit, name="service_edit"),
    path("servicios/<int:pk>/activar/", views.service_toggle, name="service_toggle"),
    path("reclamo/<int:pk>/linea/desde-servicio/", views.claimline_from_service,
         name="claimline_from_service"),
]
