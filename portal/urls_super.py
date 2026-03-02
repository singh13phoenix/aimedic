from django.urls import path
from . import views

urlpatterns = [
    path("", views.super_dashboard, name="super_dashboard"),
    path("manage/", views.super_manage, name="super_manage"),
    path("assign/", views.super_assign, name="super_assign"),
]
