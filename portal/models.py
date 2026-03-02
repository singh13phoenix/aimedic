from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Account(AbstractUser):
    class Role(models.TextChoices):
        USER = "USER", "Patient"
        DOCTOR = "DOCTOR", "Doctor"
        PHARMACY = "PHARMACY", "Drug Mart"
        SUPERADMIN = "SUPERADMIN", "Super Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    phone = models.CharField(max_length=30, blank=True)

    def is_superadmin(self):
        return self.role == self.Role.SUPERADMIN or self.is_superuser

class DoctorProfile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="doctor_profile")
    full_name = models.CharField(max_length=200)
    license_no = models.CharField(max_length=100, blank=True)
    clinic_name = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.full_name

class PharmacyProfile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="pharmacy_profile")
    store_name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.store_name

class UserProfile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="user_profile")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=300, blank=True)

    assigned_doctor = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    preferred_pharmacy = models.ForeignKey(PharmacyProfile, on_delete=models.SET_NULL, null=True, blank=True)

    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

class AppointmentRequest(models.Model):
    class Type(models.TextChoices):
        VISIT = "VISIT", "Visit Appointment"
        PHONE = "PHONE", "Phone Appointment"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=Type.choices)
    preferred_time_1 = models.DateTimeField(null=True, blank=True)
    preferred_time_2 = models.DateTimeField(null=True, blank=True)
    reason_text = models.TextField()
    ai_summary = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    doctor_response_note = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

class RefillRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        SENT_TO_PHARMACY = "SENT_TO_PHARMACY", "Sent to Drug Mart"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    doctor_note = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

class RefillInstruction(models.Model):
    class Status(models.TextChoices):
        SENT = "SENT", "Sent"
        RECEIVED = "RECEIVED", "Received"
        PREPARING = "PREPARING", "Preparing"
        READY = "READY", "Ready"
        DELIVERED = "DELIVERED", "Delivered/Picked up"
        CANCELLED = "CANCELLED", "Cancelled"

    refill_request = models.OneToOneField(RefillRequest, on_delete=models.CASCADE, related_name="instruction")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    pharmacy = models.ForeignKey(PharmacyProfile, on_delete=models.CASCADE)
    instruction_text = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

class Notification(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link_type = models.CharField(max_length=40, blank=True)
    link_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

class RecordAccessLog(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    access_type = models.CharField(max_length=40)
    query_text = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
