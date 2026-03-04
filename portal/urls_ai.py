from django.urls import path
from . import views

urlpatterns = [
    path("chat/", views.ai_chat, name="ai_chat"),
    path("doctor/patient/<int:user_id>/summary/", views.doctor_patient_summary, name="doctor_patient_summary"),
    path("user/create-appointment/", views.ai_user_create_appointment, name="ai_user_create_appointment"),
    path("user/create-refill/", views.ai_user_create_refill, name="ai_user_create_refill"),
    path("voice/patient/", views.ai_voice_patient, name="ai_voice_patient"),
]
