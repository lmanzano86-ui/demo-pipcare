from django.urls import path
from . import views

urlpatterns = [
    path("inicio/", views.dashboard, name="dashboard"),
    path("intake/", views.intake, name="intake"),
    path("paciente/<int:pk>/", views.patient_detail, name="patient_detail"),
    path("accidente/<int:pk>/", views.accident_detail, name="accident_detail"),
]
