from django.urls import path

from . import views

urlpatterns = [
    path("agenda/", views.agenda, name="agenda"),
    path("agenda/nueva/", views.appointment_create, name="appointment_create"),
    path("agenda/nueva/caso/<int:accident_pk>/", views.appointment_create,
         name="appointment_create_case"),
    path("agenda/<int:pk>/editar/", views.appointment_update, name="appointment_update"),
    path("agenda/<int:pk>/estado/", views.appointment_set_status, name="appointment_status"),
    path("agenda/recordatorios/", views.reminders_now, name="reminders_now"),
]
