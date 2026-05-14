from datetime import date, datetime
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db.models import BooleanField, DateTimeField, EmailField, TextField
from django.db.models.expressions import Combinable
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    username: TextField[str | Combinable, str] = TextField(unique=True)
    email: EmailField[str, str] = EmailField(_("email address"), unique=True)

    first_name: TextField[str | Combinable, str] = TextField(blank=True)
    last_name: TextField[str | Combinable, str] = TextField(blank=True)

    is_staff: bool | BooleanField[bool | Combinable, bool] = BooleanField(default=False)
    is_active: bool | BooleanField[bool | Combinable, bool] = BooleanField(
        default=False,
    )

    sent_email: BooleanField[bool | Combinable, bool] = BooleanField(default=False)
    date_joined: DateTimeField[str | datetime | date | Combinable, datetime] = DateTimeField(
        default=timezone.now,
    )

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["email"]

    objects = UserManager()

    def __str__(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return f"{full_name} ({self.username})" if full_name else self.username
