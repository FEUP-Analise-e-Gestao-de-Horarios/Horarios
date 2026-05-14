from typing import ClassVar

from django.contrib.auth.forms import SetPasswordForm


class SetPasswordForm(SetPasswordForm):
    class Meta:
        fields: ClassVar[list[str]] = ["new_password1", "new_password2"]
