from django.urls import path

from . import views

urlpatterns = [
    path("me", views.me, name="api-me"),
    path("login", views.login, name="api-login"),
    path("logout", views.logout, name="api-logout"),
    path("forgot-password", views.forgot_password, name="api-forgot-password"),
    path("change_password", views.change_password, name="api-change-password"),
]

# path("activate/<uidb64>/<token>", views.activate, name="activate"),
# path("forgot_password/<uidb64>/<token>", views.forgot_password_change, name="forgot_password_change"),
