from django.urls import path
from . import views

urlpatterns = [
    path("", views.pharmacy_dashboard, name="pharmacy_dashboard"),
    path("instructions/<int:pk>/", views.pharmacy_instruction_detail, name="pharmacy_instruction_detail"),
    path("instructions/<int:pk>/status/", views.pharmacy_update_status, name="pharmacy_update_status"),
    path("notifications/", views.pharmacy_notifications, name="pharmacy_notifications"),
]
