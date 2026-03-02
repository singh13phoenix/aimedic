from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from portal.models import (
    Account, UserProfile, DoctorProfile, PharmacyProfile,
    AppointmentRequest, RefillRequest, RefillInstruction
)
from portal.utils import notify

class Command(BaseCommand):
    help = "Create demo accounts and dummy data."

    def handle(self, *args, **options):
        User = get_user_model()

        def upsert(username, password, role, email):
            u, created = User.objects.get_or_create(username=username, defaults={"email": email, "role": role})
            u.email = email
            u.role = role
            u.set_password(password)
            if role == Account.Role.SUPERADMIN:
                u.is_staff = True
            u.save()
            return u

        super_u = upsert("superadmin", "Admin@12345", Account.Role.SUPERADMIN, "superadmin@example.com")
        doc_u = upsert("doctor1", "Doctor@12345", Account.Role.DOCTOR, "doctor1@example.com")
        pharm_u = upsert("pharmacy1", "Pharma@12345", Account.Role.PHARMACY, "pharmacy1@example.com")
        pat1_u = upsert("patient1", "Patient@12345", Account.Role.USER, "patient1@example.com")
        pat2_u = upsert("patient2", "Patient@12345", Account.Role.USER, "patient2@example.com")

        doctor, _ = DoctorProfile.objects.get_or_create(account=doc_u, defaults={
            "full_name": "Dr. Alex Morgan",
            "license_no": "BC-123456",
            "clinic_name": "Tech13 Family Clinic",
        })

        pharmacy, _ = PharmacyProfile.objects.get_or_create(account=pharm_u, defaults={
            "store_name": "Tech13 Drug Mart",
            "address": "123 Main St, Surrey, BC",
            "phone": "604-000-0000",
        })

        pat1, _ = UserProfile.objects.get_or_create(account=pat1_u, defaults={
            "first_name": "Jasjeet",
            "last_name": "Patient",
            "address": "Surrey, BC",
            "assigned_doctor": doctor,
            "preferred_pharmacy": pharmacy,
            "allergies": "Penicillin",
            "chronic_conditions": "High cholesterol",
        })
        pat1.assigned_doctor = doctor
        pat1.preferred_pharmacy = pharmacy
        pat1.save()

        pat2, _ = UserProfile.objects.get_or_create(account=pat2_u, defaults={
            "first_name": "Simran",
            "last_name": "Patient",
            "address": "White Rock, BC",
            "assigned_doctor": doctor,
            "preferred_pharmacy": pharmacy,
            "allergies": "",
            "chronic_conditions": "Asthma",
        })
        pat2.assigned_doctor = doctor
        pat2.preferred_pharmacy = pharmacy
        pat2.save()

        # Pending appointment & refill for patient1
        if not AppointmentRequest.objects.filter(user=pat1).exists():
            a = AppointmentRequest.objects.create(
                user=pat1,
                doctor=doctor,
                type=AppointmentRequest.Type.PHONE,
                preferred_time_1=timezone.now() + timezone.timedelta(days=1),
                preferred_time_2=timezone.now() + timezone.timedelta(days=2),
                reason_text="Fever for 2 days, mild headache.",
                ai_summary="Phone appointment request: fever 2 days + mild headache.",
                status=AppointmentRequest.Status.PENDING,
            )
            notify(doctor.account, "New Appointment Request", f"{pat1} requested a Phone Appointment.", "APPOINTMENT", a.id)

        if not RefillRequest.objects.filter(user=pat1).exists():
            r = RefillRequest.objects.create(
                user=pat1,
                doctor=doctor,
                medication_name="Atorvastatin",
                dosage="10 mg",
                frequency="Once daily",
                notes="Same dose as before.",
                ai_summary="Refill request for Atorvastatin 10mg daily (same dose).",
                status=RefillRequest.Status.PENDING,
            )
            notify(doctor.account, "New Refill Request", f"{pat1} requested refill: Atorvastatin.", "REFILL", r.id)

        # Sent instruction for patient2 (pharmacy demo)
        if not RefillRequest.objects.filter(user=pat2).exists():
            r2 = RefillRequest.objects.create(
                user=pat2,
                doctor=doctor,
                medication_name="Salbutamol Inhaler",
                dosage="100 mcg",
                frequency="As needed",
                notes="Running low.",
                ai_summary="Refill request for Salbutamol inhaler.",
                status=RefillRequest.Status.APPROVED,
                doctor_note="Approved. Standard refill.",
            )
            RefillInstruction.objects.create(
                refill_request=r2,
                doctor=doctor,
                pharmacy=pharmacy,
                instruction_text="Dispense 1 inhaler. Label: Use as directed.",
                status=RefillInstruction.Status.SENT,
            )
            r2.status = RefillRequest.Status.SENT_TO_PHARMACY
            r2.save()

        self.stdout.write(self.style.SUCCESS("✅ Demo data created. See README for credentials."))
