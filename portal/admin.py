from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Account, UserProfile, DoctorProfile, PharmacyProfile,
    AppointmentRequest, RefillRequest, RefillInstruction,
    Notification, RecordAccessLog
)

@admin.register(Account)
class AccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Role & Contact", {"fields": ("role", "phone")}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")

admin.site.register(UserProfile)
admin.site.register(DoctorProfile)
admin.site.register(PharmacyProfile)
admin.site.register(AppointmentRequest)
admin.site.register(RefillRequest)
admin.site.register(RefillInstruction)
admin.site.register(Notification)
admin.site.register(RecordAccessLog)
