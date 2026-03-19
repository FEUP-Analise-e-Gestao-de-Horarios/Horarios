from django.urls import path

from . import views

# urls for auth
urlpatterns = [
    path("me", views.me, name="api-me"),
    path("login", views.login, name="api-login"),
    path("logout", views.logout, name="api-logout"),
    path("forgot-password", views.ForgotPasswordView.as_view(), name="api-forgot-password"),
    path("activate/<uidb64>/<token>", views.activate, name="activate"),
    path(
        "forgot_password/<uidb64>/<token>",
        views.forgot_password_change,
        name="forgot_password_change",
    ),
    path("password_change", views.password_change, name="password_change"),
    path("change_password", views.password_change_no_old_pass, name="password_change_no_old_pass"),
]
