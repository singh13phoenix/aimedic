from django.urls import path
from . import views

urlpatterns = [
    path("", views.doctor_dashboard, name="doctor_dashboard"),
    path("appointments/<int:pk>/", views.doctor_appointment_detail, name="doctor_appointment_detail"),
    path("appointments/<int:pk>/action/", views.doctor_appointment_action, name="doctor_appointment_action"),
    path("refills/<int:pk>/", views.doctor_refill_detail, name="doctor_refill_detail"),
    path("refills/<int:pk>/action/", views.doctor_refill_action, name="doctor_refill_action"),
    path("notifications/", views.doctor_notifications, name="doctor_notifications"),
]
