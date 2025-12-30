from django.urls import path
from django.contrib.auth import views as auth_views

from .views import HomeDashboardView

urlpatterns = [
    path("", HomeDashboardView.as_view(), name="home"),

    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),

    # POST: logout real (Django 6)
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Password change using Django built-in views
    path(
        "accounts/password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html"
        ),
        name="password_change",
    ),

    path(
        "accounts/password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
]
