import json

from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.http import require_GET, require_POST

from src.config.settings import base
from src.core.errors import ApiError, ErrorResponse, NotAuthenticatedResponse
from src.login.tokens import generate_token
from src.users.models import User


@require_GET
def me(request) -> JsonResponse:
    if not request.user.is_authenticated:
        return NotAuthenticatedResponse()

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
        return ErrorResponse(status=400, code=ApiError.INVALID_JSON, message="Invalid JSON.")

    username = data.get("username", "")
    password = data.get("password", "")

    user = authenticate(username=username, password=password)
    if user is not None:
        django_login(request, user)
        return JsonResponse({"ok": True, "username": user.username})

    return ErrorResponse(
        status=401,
        code=ApiError.AUTH_BAD_CREDENTIALS,
        message="Invalid username or password.",
    )


@require_POST
def logout(request) -> JsonResponse:
    django_logout(request)
    return JsonResponse({"ok": True})


@require_POST
def forgot_password(request) -> JsonResponse:
    if request.user.is_authenticated:
        return ErrorResponse(
            status=400,
            code=ApiError.AUTH_ALREADY_AUTHENTICATED,
            message="Already authenticated.",
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return ErrorResponse(status=400, code=ApiError.INVALID_JSON, message="Invalid JSON.")

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


@require_POST
def change_password(request) -> JsonResponse:
    if not request.user.is_authenticated:
        return NotAuthenticatedResponse()

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return ErrorResponse(status=400, code=ApiError.INVALID_JSON, message="Invalid JSON.")

    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not request.user.check_password(old_password):
        return ErrorResponse(
            status=401,
            code=ApiError.AUTH_INVALID_OLD_PASSWORD,
            message="Incorrect old password.",
        )

    form = PasswordChangeForm(
        user=request.user,
        data={
            "old_password": old_password,
            "new_password1": new_password,
            "new_password2": new_password,
        },
    )

    if not form.is_valid():
        errors = [e for error_list in form.errors.values() for e in error_list]
        return ErrorResponse(
            status=400,
            code=ApiError.AUTH_PASSWORD_POLICY_VIOLATION,
            message=errors[0],
        )

    form.save()
    update_session_auth_hash(request, form.user)
    return JsonResponse({"ok": True})
