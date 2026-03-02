from django.contrib import admin
from django.urls import path, include
from portal import views as portal_views

urlpatterns = [
    path("", portal_views.home, name="home"),
    path("admin/", admin.site.urls),

    path("login/user/", portal_views.role_login, {"role": "USER"}, name="login_user"),
    path("login/doctor/", portal_views.role_login, {"role": "DOCTOR"}, name="login_doctor"),
    path("login/pharmacy/", portal_views.role_login, {"role": "PHARMACY"}, name="login_pharmacy"),
    path("login/super/", portal_views.role_login, {"role": "SUPERADMIN"}, name="login_super"),

    path("logout/", portal_views.logout_view, name="logout"),

    path("user/", include("portal.urls_user")),
    path("doctor/", include("portal.urls_doctor")),
    path("pharmacy/", include("portal.urls_pharmacy")),
    path("super/", include("portal.urls_super")),

    path("ai/", include("portal.urls_ai")),
]
