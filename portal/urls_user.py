from django.urls import path
from . import views

urlpatterns = [
    path("", views.user_dashboard, name="user_dashboard"),
    path("appointment/new/", views.user_appointment_new, name="user_appointment_new"),
    path("refill/new/", views.user_refill_new, name="user_refill_new"),
    path("requests/", views.user_requests, name="user_requests"),
    path("notifications/", views.user_notifications, name="user_notifications"),
]
