from django.urls import path
from . import views

urlpatterns = [
    path("accidente/<int:accident_pk>/visita/nueva/", views.visit_create, name="visit_create"),
    path("visita/<int:visit_pk>/soap/", views.soap_note, name="soap_note"),
    path("accidente/<int:accident_pk>/medicion/nueva/", views.outcome_create, name="outcome_create"),
    path("accidente/<int:accident_pk>/plan/nuevo/", views.plan_create, name="plan_create"),
    path("plan/<int:pk>/sesion/", views.plan_add_session, name="plan_add_session"),
    path("plan/<int:pk>/estado/", views.plan_set_status, name="plan_set_status"),
]
