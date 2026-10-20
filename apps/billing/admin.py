from django.contrib import admin
from .models import Claim, ClaimLine, Payment, Denial, EDITransmission

admin.site.register(Claim)
admin.site.register(ClaimLine)
admin.site.register(Payment)
admin.site.register(Denial)
admin.site.register(EDITransmission)
