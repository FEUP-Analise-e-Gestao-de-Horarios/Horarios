import json

from django.contrib import messages
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.decorators.http import require_GET, require_POST

from src.config.settings import base
from src.login.tokens import generate_token
from src.users.models import User


@require_GET
def me(request) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    user = request.user
    return JsonResponse(
        {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
    )


@require_POST
def login(request) -> JsonResponse:
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = data.get("username", "")
    password = data.get("password", "")

    user = authenticate(username=username, password=password)
    if user is not None:
        django_login(request, user)
        return JsonResponse({"ok": True, "username": user.username})

    return JsonResponse({"error": "Bad Credentials!"}, status=401)


@require_POST
def logout(request) -> JsonResponse:
    django_logout(request)
    return JsonResponse({"ok": True})


class ForgotPasswordView(View):
    def post(self, request):
        if request.user.is_authenticated:
            return redirect("/")

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        email_addr = data.get("email", "")

        if User.objects.filter(email=email_addr).exists():
            user = User.objects.get(email__exact=email_addr)
            email_subject = "Forgot password"
            email_message = render_to_string(
                "login/email_forgot_password.html",
                {
                    "name": user.username,
                    "domain": "10.227.107.115",
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": generate_token.make_token(user),
                },
            )
            email = EmailMessage(
                email_subject,
                email_message,
                base.EMAIL_HOST_USER,
                [email_addr],
            )
            email.fail_silently = True
            email.send()

        return JsonResponse({"detail": "ok"})


# activates the user through a token by adding their id to the Person object
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        myuser = User.objects.get(pk=uid)
    except TypeError, ValueError, OverflowError, User.DoesNotExist:
        myuser = None

    if myuser is not None and generate_token.check_token(myuser, token):
        myuser.is_active = True
        # user.profile.signup_confirmation = True
        myuser.save()
        login(request, myuser)
        # messages.success(request, "Your Account has been activated!!")
        return redirect("password_change")
    else:
        return redirect("login")


# Change password of user (asks the old password)
def password_change(request):
    if not request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            # messages.success(request, 'Your password was successfully updated!')
            return redirect("/")
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, "login/password_reset.html", {"form": form})


# Change password of user (does not ask the old password)
def password_change_no_old_pass(request):
    if not request.user.is_authenticated:
        return redirect("/")

    myuser = request.user
    logout(request)

    if request.method == "POST":
        form = SetPasswordForm(myuser, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "Your password was successfully updated!")
            return redirect("/")
    else:
        form = SetPasswordForm(myuser)
    login(request, myuser)
    return render(request, "login/password_reset.html", {"form": form})


# checks if the token is valid and redirects to reset password (no old password )
def forgot_password_change(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        myuser = User.objects.get(pk=uid)
    except TypeError, ValueError, OverflowError, User.DoesNotExist:
        myuser = None

    if myuser is not None and generate_token.check_token(myuser, token):
        login(request, myuser)
        return redirect("password_change_no_old_pass")
    else:
        return redirect("login")
