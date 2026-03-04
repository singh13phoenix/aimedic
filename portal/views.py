import json
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden

from .models import (
    Account, UserProfile, DoctorProfile, PharmacyProfile,
    AppointmentRequest, RefillRequest, RefillInstruction,
    Notification, RecordAccessLog
)
from .forms import RoleLoginForm, AppointmentRequestForm, RefillRequestForm
from .decorators import role_required
from .utils import notify

def home(request):
    if not request.user.is_authenticated:
        return render(request, "landing.html")

    role = request.user.role
    if role == Account.Role.USER:
        return redirect("user_dashboard")
    if role == Account.Role.DOCTOR:
        return redirect("doctor_dashboard")
    if role == Account.Role.PHARMACY:
        return redirect("pharmacy_dashboard")
    if role == Account.Role.SUPERADMIN or request.user.is_superuser:
        return redirect("super_dashboard")
    return render(request, "landing.html")

def role_login(request, role):
    form = RoleLoginForm(request, data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()

            if role == "SUPERADMIN":
                if user.is_superuser or getattr(user, "role", None) == Account.Role.SUPERADMIN:
                    login(request, user)
                    return redirect("super_dashboard")
                messages.error(request, "This account is not a Super Admin.")
                return redirect("login_super")

            if getattr(user, "role", None) != role and not user.is_superuser:
                messages.error(request, f"This login page is for {role.lower()} accounts.")
                return redirect(request.path)

            login(request, user)
            return redirect("home")

        messages.error(request, "Invalid username/password.")

    return render(request, "auth/role_login.html", {"form": form, "role": role})

def logout_view(request):
    logout(request)
    return redirect("home")

# ---------------- PATIENT PORTAL ----------------
@role_required(Account.Role.USER)
def user_dashboard(request):
    profile = get_object_or_404(UserProfile, account=request.user)
    return render(request, "user/dashboard.html", {"profile": profile})

@role_required(Account.Role.USER)
def user_appointment_new(request):
    profile = get_object_or_404(UserProfile, account=request.user)
    if not profile.assigned_doctor:
        messages.error(request, "No assigned doctor. Ask Super Admin to assign a doctor.")
        return redirect("user_dashboard")

    initial_type = request.GET.get("type")
    form = AppointmentRequestForm(request.POST or None, initial={"type": initial_type} if initial_type else None)

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = profile
        obj.doctor = profile.assigned_doctor
        obj.status = AppointmentRequest.Status.PENDING
        obj.save()

        notify(profile.assigned_doctor.account, "New Appointment Request",
               f"{profile} requested a {obj.get_type_display()} appointment.", "APPOINTMENT", obj.id)
        messages.success(request, "Request submitted. Your doctor will review it.")
        return redirect("user_requests")

    return render(request, "user/appointment_new.html", {"form": form, "profile": profile})

@role_required(Account.Role.USER)
def user_refill_new(request):
    profile = get_object_or_404(UserProfile, account=request.user)
    if not profile.assigned_doctor:
        messages.error(request, "No assigned doctor. Ask Super Admin to assign a doctor.")
        return redirect("user_dashboard")

    form = RefillRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = profile
        obj.doctor = profile.assigned_doctor
        obj.status = RefillRequest.Status.PENDING
        obj.save()

        notify(profile.assigned_doctor.account, "New Refill Request",
               f"{profile} requested refill: {obj.medication_name}.", "REFILL", obj.id)
        messages.success(request, "Refill request submitted. Your doctor will review it.")
        return redirect("user_requests")

    return render(request, "user/refill_new.html", {"form": form, "profile": profile})

@role_required(Account.Role.USER)
def user_requests(request):
    profile = get_object_or_404(UserProfile, account=request.user)
    appts = AppointmentRequest.objects.filter(user=profile).order_by("-created_at")
    refills = RefillRequest.objects.filter(user=profile).order_by("-created_at")
    return render(request, "user/requests.html", {"profile": profile, "appts": appts, "refills": refills})

@role_required(Account.Role.USER)
def user_notifications(request):
    notes = Notification.objects.filter(account=request.user).order_by("-created_at")[:200]
    if request.method == "POST":
        Notification.objects.filter(account=request.user, is_read=False).update(is_read=True)
        return redirect("user_notifications")
    return render(request, "common/notifications.html", {"notes": notes, "portal_title": "Patient Notifications"})

# ---------------- DOCTOR PORTAL ----------------
@role_required(Account.Role.DOCTOR)
def doctor_dashboard(request):
    doctor = get_object_or_404(DoctorProfile, account=request.user)
    appts = AppointmentRequest.objects.filter(doctor=doctor, status=AppointmentRequest.Status.PENDING).order_by("-created_at")
    refills = RefillRequest.objects.filter(doctor=doctor, status=RefillRequest.Status.PENDING).order_by("-created_at")
    return render(request, "doctor/dashboard.html", {"doctor": doctor, "appts": appts, "refills": refills})

@role_required(Account.Role.DOCTOR)
def doctor_appointment_detail(request, pk):
    doctor = get_object_or_404(DoctorProfile, account=request.user)
    obj = get_object_or_404(AppointmentRequest, pk=pk, doctor=doctor)
    return render(request, "doctor/appointment_detail.html", {"doctor": doctor, "obj": obj})

@role_required(Account.Role.DOCTOR)
@require_POST
def doctor_appointment_action(request, pk):
    doctor = get_object_or_404(DoctorProfile, account=request.user)
    obj = get_object_or_404(AppointmentRequest, pk=pk, doctor=doctor)
    action = request.POST.get("action")
    note = request.POST.get("note", "")
    scheduled_at = request.POST.get("scheduled_at", "")

    if action == "approve":
        obj.status = AppointmentRequest.Status.APPROVED
        obj.doctor_response_note = note
        if scheduled_at:
            try:
                dt = timezone.datetime.fromisoformat(scheduled_at)
                if dt.tzinfo is None:
                    dt = timezone.make_aware(dt)
                obj.scheduled_at = dt
            except Exception:
                pass
        obj.save()
        notify(obj.user.account, "Appointment Approved",
               f"Your {obj.get_type_display()} request was approved. {('Scheduled at: ' + str(obj.scheduled_at)) if obj.scheduled_at else ''}",
               "APPOINTMENT", obj.id)
        messages.success(request, "Approved and patient notified.")
    elif action == "reject":
        obj.status = AppointmentRequest.Status.REJECTED
        obj.doctor_response_note = note
        obj.save()
        notify(obj.user.account, "Appointment Rejected",
               f"Your appointment request was rejected. Note: {note}", "APPOINTMENT", obj.id)
        messages.success(request, "Rejected and patient notified.")
    else:
        return HttpResponseBadRequest("Unknown action")

    return redirect("doctor_dashboard")

@role_required(Account.Role.DOCTOR)
def doctor_refill_detail(request, pk):
    doctor = get_object_or_404(DoctorProfile, account=request.user)
    obj = get_object_or_404(RefillRequest, pk=pk, doctor=doctor)
    RecordAccessLog.objects.create(doctor=doctor, user=obj.user, access_type="SUMMARY", query_text="Opened refill detail")
    return render(request, "doctor/refill_detail.html", {"doctor": doctor, "obj": obj})

@role_required(Account.Role.DOCTOR)
@require_POST
def doctor_refill_action(request, pk):
    doctor = get_object_or_404(DoctorProfile, account=request.user)
    obj = get_object_or_404(RefillRequest, pk=pk, doctor=doctor)
    action = request.POST.get("action")
    note = request.POST.get("note", "")
    instruction_text = request.POST.get("instruction_text", "")

    if action == "approve":
        obj.status = RefillRequest.Status.APPROVED
        obj.doctor_note = note
        obj.save()
        notify(obj.user.account, "Refill Approved", f"Your refill request was approved. {note}", "REFILL", obj.id)
        messages.success(request, "Approved and patient notified.")
    elif action == "reject":
        obj.status = RefillRequest.Status.REJECTED
        obj.doctor_note = note
        obj.save()
        notify(obj.user.account, "Refill Rejected", f"Your refill request was rejected. Note: {note}", "REFILL", obj.id)
        messages.success(request, "Rejected and patient notified.")
    elif action == "send_to_pharmacy":
        if obj.status not in [RefillRequest.Status.APPROVED, RefillRequest.Status.SENT_TO_PHARMACY]:
            messages.error(request, "Approve refill first before sending to pharmacy.")
            return redirect("doctor_refill_detail", pk=obj.id)

        pharmacy = obj.user.preferred_pharmacy
        if pharmacy is None:
            messages.error(request, "Patient has no preferred drug mart. Super Admin can assign one.")
            return redirect("doctor_refill_detail", pk=obj.id)

        if not instruction_text.strip():
            instruction_text = f"Refill: {obj.medication_name} {obj.dosage} {obj.frequency}".strip()

        inst, created = RefillInstruction.objects.get_or_create(
            refill_request=obj,
            defaults={"doctor": doctor, "pharmacy": pharmacy, "instruction_text": instruction_text}
        )
        if not created:
            inst.instruction_text = instruction_text
            inst.pharmacy = pharmacy
            inst.doctor = doctor
            inst.status = RefillInstruction.Status.SENT
            inst.save()

        obj.status = RefillRequest.Status.SENT_TO_PHARMACY
        obj.save()

        notify(pharmacy.account, "New Refill Instruction",
               f"Instruction from Dr. {doctor.full_name}: {instruction_text}",
               "REFILL", obj.id)
        notify(obj.user.account, "Refill Sent to Drug Mart",
               f"Your refill was sent to {pharmacy.store_name}.", "REFILL", obj.id)
        messages.success(request, "Sent to drug mart and notifications delivered.")
    else:
        return HttpResponseBadRequest("Unknown action")

    return redirect("doctor_dashboard")

@role_required(Account.Role.DOCTOR)
def doctor_notifications(request):
    notes = Notification.objects.filter(account=request.user).order_by("-created_at")[:200]
    if request.method == "POST":
        Notification.objects.filter(account=request.user, is_read=False).update(is_read=True)
        return redirect("doctor_notifications")
    return render(request, "common/notifications.html", {"notes": notes, "portal_title": "Doctor Notifications"})

# ---------------- PHARMACY PORTAL ----------------
@role_required(Account.Role.PHARMACY)
def pharmacy_dashboard(request):
    pharmacy = get_object_or_404(PharmacyProfile, account=request.user)
    instructions = RefillInstruction.objects.filter(pharmacy=pharmacy).order_by("-created_at")[:200]
    return render(request, "pharmacy/dashboard.html", {"pharmacy": pharmacy, "instructions": instructions})

@role_required(Account.Role.PHARMACY)
def pharmacy_instruction_detail(request, pk):
    pharmacy = get_object_or_404(PharmacyProfile, account=request.user)
    obj = get_object_or_404(RefillInstruction, pk=pk, pharmacy=pharmacy)
    return render(request, "pharmacy/instruction_detail.html", {"pharmacy": pharmacy, "obj": obj})

@role_required(Account.Role.PHARMACY)
@require_POST
def pharmacy_update_status(request, pk):
    pharmacy = get_object_or_404(PharmacyProfile, account=request.user)
    obj = get_object_or_404(RefillInstruction, pk=pk, pharmacy=pharmacy)
    new_status = request.POST.get("status")
    allowed = {v for v, _ in RefillInstruction.Status.choices}
    if new_status not in allowed:
        return HttpResponseBadRequest("Bad status")

    obj.status = new_status
    obj.save()

    notify(obj.refill_request.user.account, "Refill Status Updated",
           f"Drug mart updated status to: {obj.get_status_display()}",
           "REFILL", obj.refill_request.id)
    notify(obj.doctor.account, "Refill Status Updated",
           f"Drug mart status: {obj.get_status_display()} for {obj.refill_request.user}",
           "REFILL", obj.refill_request.id)

    messages.success(request, "Status updated and notifications sent.")
    return redirect("pharmacy_dashboard")

@role_required(Account.Role.PHARMACY)
def pharmacy_notifications(request):
    notes = Notification.objects.filter(account=request.user).order_by("-created_at")[:200]
    if request.method == "POST":
        Notification.objects.filter(account=request.user, is_read=False).update(is_read=True)
        return redirect("pharmacy_notifications")
    return render(request, "common/notifications.html", {"notes": notes, "portal_title": "Drug Mart Notifications"})

# ---------------- SUPER ADMIN PORTAL ----------------
@role_required(Account.Role.SUPERADMIN)
def super_dashboard(request):
    return render(request, "super/dashboard.html", {
        "users": UserProfile.objects.count(),
        "doctors": DoctorProfile.objects.count(),
        "pharmacies": PharmacyProfile.objects.count(),
        "pending_appts": AppointmentRequest.objects.filter(status=AppointmentRequest.Status.PENDING).count(),
        "pending_refills": RefillRequest.objects.filter(status=RefillRequest.Status.PENDING).count(),
    })

@role_required(Account.Role.SUPERADMIN)
def super_manage(request):
    users = UserProfile.objects.select_related("account", "assigned_doctor", "preferred_pharmacy").order_by("last_name", "first_name")
    doctors = DoctorProfile.objects.select_related("account").order_by("full_name")
    pharmacies = PharmacyProfile.objects.select_related("account").order_by("store_name")
    return render(request, "super/manage.html", {"users": users, "doctors": doctors, "pharmacies": pharmacies})

@role_required(Account.Role.SUPERADMIN)
@require_POST
def super_assign(request):
    user_id = request.POST.get("user_id")
    doctor_id = request.POST.get("doctor_id") or None
    pharmacy_id = request.POST.get("pharmacy_id") or None

    u = get_object_or_404(UserProfile, pk=user_id)
    u.assigned_doctor = DoctorProfile.objects.filter(pk=doctor_id).first() if doctor_id else None
    u.preferred_pharmacy = PharmacyProfile.objects.filter(pk=pharmacy_id).first() if pharmacy_id else None
    u.save()

    messages.success(request, "Assignments updated.")
    return redirect("super_manage")

# ---------------- AI ENDPOINTS (MOCK scaffold) ----------------
def ai_chat(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    if not request.user.is_authenticated:
        return JsonResponse({"error":"auth"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error":"bad_json"}, status=400)

    text = (payload.get("text") or "").strip()
    mode = payload.get("mode") or "user"
    if not text:
        return JsonResponse({"reply":"Please say something."})

    lower = text.lower()

    if mode == "user" and request.user.role == Account.Role.USER:
        if "refill" in lower:
            return JsonResponse({"reply":"Okay. Please tell me medicine name, dosage and frequency."})
        if "phone" in lower:
            return JsonResponse({"reply":"Phone appointment. Tell me preferred time and reason."})
        if "visit" in lower or "in person" in lower:
            return JsonResponse({"reply":"Visit appointment. Tell me preferred time and reason."})
        return JsonResponse({"reply":"You can say: visit appointment, phone appointment, or refill medicine."})

    if mode == "doctor" and request.user.role == Account.Role.DOCTOR:
        if "history" in lower or "previous" in lower or "record" in lower:
            return JsonResponse({"reply":"Say: allergies, chronic conditions, or recent refills for this patient."})
        if "approve" in lower:
            return JsonResponse({"reply":"Okay. Open the request and click approve, or say: 'approve appointment ID' (feature ready for next step)."})
        return JsonResponse({"reply":"You can say: approve, reject, send to pharmacy, or ask for patient history."})

    return JsonResponse({"reply":"AI mode not allowed for this role."}, status=403)

def doctor_patient_summary(request, user_id):
    if request.method != "GET":
        return HttpResponseBadRequest("GET only")
    if request.user.role != Account.Role.DOCTOR and not request.user.is_superuser:
        return JsonResponse({"error":"forbidden"}, status=403)

    doctor = get_object_or_404(DoctorProfile, account=request.user)
    patient = get_object_or_404(UserProfile, pk=user_id)

    if patient.assigned_doctor_id != doctor.id:
        return JsonResponse({"error":"not_assigned"}, status=403)

    RecordAccessLog.objects.create(doctor=doctor, user=patient, access_type="SUMMARY", query_text="Doctor requested summary via API")

    return JsonResponse({
        "patient": str(patient),
        "allergies": patient.allergies,
        "chronic_conditions": patient.chronic_conditions,
    })

# ---------------- AI Voice assistant start ----------------
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY",""))

def _tool_create_appointment(request, args):
    profile = get_object_or_404(UserProfile, account=request.user)
    if not profile.assigned_doctor:
        return {"error": "no_assigned_doctor"}

    obj = AppointmentRequest.objects.create(
        user=profile,
        doctor=profile.assigned_doctor,
        type=args.get("type","PHONE"),
        reason_text=args.get("reason_text",""),
        status=AppointmentRequest.Status.PENDING,
        ai_summary=args.get("ai_summary",""),
    )
    notify(profile.assigned_doctor.account, "New Appointment Request",
           f"{profile} requested a {obj.get_type_display()} appointment.", "APPOINTMENT", obj.id)
    return {"appointment_id": obj.id}

def _tool_create_refill(request, args):
    profile = get_object_or_404(UserProfile, account=request.user)
    if not profile.assigned_doctor:
        return {"error": "no_assigned_doctor"}

    obj = RefillRequest.objects.create(
        user=profile,
        doctor=profile.assigned_doctor,
        medication_name=args.get("medication_name",""),
        dosage=args.get("dosage",""),
        frequency=args.get("frequency",""),
        notes=args.get("notes",""),
        status=RefillRequest.Status.PENDING,
        ai_summary=args.get("ai_summary",""),
    )
    notify(profile.assigned_doctor.account, "New Refill Request",
           f"{profile} requested refill: {obj.medication_name}.", "REFILL", obj.id)
    return {"refill_id": obj.id}

@csrf_exempt
def ai_voice_patient(request):
    if request.method != "POST":
        return JsonResponse({"error":"POST only"}, status=400)
    if not request.user.is_authenticated or request.user.role != Account.Role.USER:
        return JsonResponse({"error":"forbidden"}, status=403)

    payload = json.loads(request.body.decode("utf-8"))
    text = (payload.get("text") or "").strip()
    if not text:
        return JsonResponse({"reply":"Please say something."})

    tools = [
        {
            "type": "function",
            "function": {
                "name": "create_appointment_request",
                "description": "Create a new appointment request (visit or phone) for the logged-in patient.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {"type":"string","enum":["VISIT","PHONE"]},
                        "reason_text": {"type":"string"},
                        "ai_summary": {"type":"string"},
                    },
                    "required": ["type","reason_text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_refill_request",
                "description": "Create a new refill request for the logged-in patient.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "medication_name": {"type":"string"},
                        "dosage": {"type":"string"},
                        "frequency": {"type":"string"},
                        "notes": {"type":"string"},
                        "ai_summary": {"type":"string"},
                    },
                    "required": ["medication_name"]
                }
            }
        },
    ]

    system = (
        "You are a voice assistant for a medical portal. "
        "Your job: help the patient create either an appointment request (VISIT or PHONE) "
        "or a refill request. Ask short follow-up questions if required fields are missing. "
        "When ready, call the appropriate tool. Keep replies short and friendly."
    )

    # First model call
    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role":"system","content": system},
            {"role":"user","content": text},
        ],
        tools=tools
    )

    # If tool called, execute it
    if resp.output and len(resp.output) > 0:
        for item in resp.output:
            if item.type == "function_call":
                fn = item.name
                args = item.arguments or {}
                if isinstance(args, str):
                    args = json.loads(args)

                if fn == "create_appointment_request":
                    result = _tool_create_appointment(request, args)
                elif fn == "create_refill_request":
                    result = _tool_create_refill(request, args)
                else:
                    result = {"error":"unknown_tool"}

                # Send tool result back for final message
                resp2 = client.responses.create(
                    model="gpt-4o-mini",
                    input=[
                        {"role":"system","content": system},
                        {"role":"user","content": text},
                        {"role":"tool","name": fn, "content": json.dumps(result)},
                    ],
                    tools=tools
                )

                final_text = ""
                if resp2.output_text:
                    final_text = resp2.output_text
                else:
                    final_text = "Done."

                return JsonResponse({"reply": final_text, "done": True, "result": result})

    # No tool call → assistant question
    return JsonResponse({"reply": resp.output_text or "Please tell me what you want to do."})

from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime

@csrf_exempt
def ai_user_create_appointment(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)
    if not request.user.is_authenticated or request.user.role != Account.Role.USER:
        return JsonResponse({"error": "forbidden"}, status=403)

    profile = get_object_or_404(UserProfile, account=request.user)
    if not profile.assigned_doctor:
        return JsonResponse({"error": "no_assigned_doctor"}, status=400)

    payload = json.loads(request.body.decode("utf-8"))
    appt_type = payload.get("type")  # VISIT or PHONE
    reason = payload.get("reason_text", "")
    t1 = payload.get("preferred_time_1")
    t2 = payload.get("preferred_time_2")

    obj = AppointmentRequest.objects.create(
        user=profile,
        doctor=profile.assigned_doctor,
        type=appt_type,
        reason_text=reason,
        preferred_time_1=parse_datetime(t1) if t1 else None,
        preferred_time_2=parse_datetime(t2) if t2 else None,
        status=AppointmentRequest.Status.PENDING,
        ai_summary=payload.get("ai_summary","")
    )

    notify(profile.assigned_doctor.account, "New Appointment Request",
           f"{profile} requested a {obj.get_type_display()} appointment.", "APPOINTMENT", obj.id)

    return JsonResponse({"ok": True, "appointment_id": obj.id})


@csrf_exempt
def ai_user_create_refill(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)
    if not request.user.is_authenticated or request.user.role != Account.Role.USER:
        return JsonResponse({"error": "forbidden"}, status=403)

    profile = get_object_or_404(UserProfile, account=request.user)
    if not profile.assigned_doctor:
        return JsonResponse({"error": "no_assigned_doctor"}, status=400)

    payload = json.loads(request.body.decode("utf-8"))
    obj = RefillRequest.objects.create(
        user=profile,
        doctor=profile.assigned_doctor,
        medication_name=payload.get("medication_name",""),
        dosage=payload.get("dosage",""),
        frequency=payload.get("frequency",""),
        notes=payload.get("notes",""),
        status=RefillRequest.Status.PENDING,
        ai_summary=payload.get("ai_summary",""),
    )

    notify(profile.assigned_doctor.account, "New Refill Request",
           f"{profile} requested refill: {obj.medication_name}.", "REFILL", obj.id)

    return JsonResponse({"ok": True, "refill_id": obj.id})

# ---------------- AI Voice assistant end ----------------