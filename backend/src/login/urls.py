from django.urls import path
from . import views

#urls for auth
urlpatterns = [
    path('', views.signin , name="signin"),
    path('signout', views.signout , name="signout"),
    path('activate/<uidb64>/<token>', views.activate , name="activate"),
    path('forgot_password/<uidb64>/<token>', views.forgot_password_change , name="forgot_password_change"),
    path("password_change", views.password_change, name="password_change"),
    path("change_password", views.password_change_no_old_pass, name="password_change_no_old_pass"),
    path("forgot_password", views.forgot_password, name="forgot_password"),
]