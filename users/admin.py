from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser
from django.http import HttpResponseRedirect
from FeupScheduleEditor import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from login.tokens import generate_token
import random
import string

admin.site.unregister(Group)

admin.site.unregister(Site)

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("username", "is_staff", "is_active", "sent_email", "is_superuser")
    list_filter = ("username", "is_staff", "is_active", "sent_email", "is_superuser")
    fieldsets = (
        (None, {"fields": ("email", "password", "username", "first_name", "last_name")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "sent_email", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide"),
            "fields": (
                "email", "password1", "password2" , "username", "first_name", "last_name", "is_staff",
                "is_active", "sent_email", "is_superuser"
            )}
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)

    actions = ['send_confirmation_email']

    # sends a email to activate the users account
    def send_confirmation_email(self, request, queryset):
        # All requests here will actually be of type POST 
        # so we will need to check for our special key 'apply' 
        # rather than the actual request type
        # The user clicked submit on the intermediate form.
        # Perform our update action:
        #WELCOME email
        queryset.update(sent_email = True)
        for users in queryset:
            if (users.is_active):
                continue
            letters = string.ascii_lowercase
            result_str = ''.join(random.choice(letters) for i in range(10))
            users.set_password(result_str)
            users.save()
            email_subject = "Welcome to feup Scheduler"
            email_message = render_to_string('login/email_confirmation.html',{
                'name' : users.username,
                'password' : result_str,
                'domain' : "10.227.107.115",
                'uid' : urlsafe_base64_encode(force_bytes(users.pk)),
                'token': generate_token.make_token(users)
            })
            email = EmailMessage(
                email_subject,
                email_message,
                settings.EMAIL_HOST_USER,
                [users.email],
            )
            email.fail_silently = True
            email.send()
        
        # Redirect to our admin view after our update has 
        # completed with a nice little info message saying 
        # our models have been updated:
        self.message_user(request,
                            "Sent email".format(queryset.count()))
        return HttpResponseRedirect(request.get_full_path())

    send_confirmation_email.short_description = "Send confirmation email"


admin.site.register(CustomUser, CustomUserAdmin)