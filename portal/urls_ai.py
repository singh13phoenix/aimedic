from django.urls import path
from . import views

urlpatterns = [
    path("chat/", views.ai_chat, name="ai_chat"),
    path("doctor/patient/<int:user_id>/summary/", views.doctor_patient_summary, name="doctor_patient_summary"), 
    path("voice/patient/", views.ai_voice_patient, name="ai_voice_patient"),
    
]
