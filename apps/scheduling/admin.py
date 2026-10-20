from django.contrib import admin

from .models import Appointment, ReminderLog


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("date", "start_time", "patient", "provider", "appt_type", "status")
    list_filter = ("date", "status", "appt_type", "provider")


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ("sent_at", "appointment", "to_phone", "ok")
    list_filter = ("ok",)
