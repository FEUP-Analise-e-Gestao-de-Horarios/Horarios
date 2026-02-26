from django.shortcuts import render, redirect
from users.models import CustomUser
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth import authenticate, login, logout
from . tokens import generate_token
from core.models import Person
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth import update_session_auth_hash

from FeupScheduleEditor import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from login.tokens import generate_token


# signin page
def signin(request):

    if (request.user.is_authenticated):
        return redirect('/')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['pass']

        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/')

        else:
            messages.error(request, "Bad Credentials!")
            return redirect('signin')

    return render(request, 'login/signin.html')


# signouts the user
def signout(request):
    logout(request)
    messages.success(request, "Logged out")
    return redirect('signin')

# activates the user through a token by adding their id to the Person object
def activate(request,uidb64,token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        myuser = CustomUser.objects.get(pk=uid)
    except (TypeError,ValueError,OverflowError,CustomUser.DoesNotExist):
        myuser = None

    if myuser is not None and generate_token.check_token(myuser,token):
        myuser.is_active = True
        # user.profile.signup_confirmation = True
        myuser.save()
        login(request,myuser)
        custom = Person.objects.create(username = myuser)
        custom.save()
        #messages.success(request, "Your Account has been activated!!")
        return redirect('password_change')
    else:
        return redirect('signin')

# Change password of user (asks the old password)
def password_change(request):
    if (not request.user.is_authenticated):
        return redirect('/')
    
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            #messages.success(request, 'Your password was successfully updated!')
            return redirect('/')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'login/password_reset.html', {'form': form})

# asks for email and sends an email to change password
def forgot_password(request):
    if (request.user.is_authenticated):
        return redirect('/')
    
    if request.method == 'POST':
        if CustomUser.objects.filter(email=request.POST['email']).exists():
            user = CustomUser.objects.get(email__exact=request.POST['email'])
            email_subject = "Forgot password"
            email_message = render_to_string('login/email_forgot_password.html',{
                'name' : user.username,
                'domain' : "10.227.107.115",
                'uid' : urlsafe_base64_encode(force_bytes(user.pk)),
                'token': generate_token.make_token(user)
            })
            email = EmailMessage(
                email_subject,
                email_message,
                settings.EMAIL_HOST_USER,
                [request.POST['email']],
            )
            email.fail_silently = True
            email.send()
            return redirect('signin')
        else:
            messages.error(request, 'Email doesn\'t exist')
            return render(request, 'login/forgot_password.html')
    else:
        return render(request, 'login/forgot_password.html')

# Change password of user (does not ask the old password)
def password_change_no_old_pass(request):
    if (not request.user.is_authenticated):
        return redirect('/')
    
    myuser = request.user
    logout(request)
    
    if request.method == 'POST':
        form = SetPasswordForm(myuser, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('/')
    else:
        form = SetPasswordForm(myuser)
    login(request,myuser)
    return render(request, 'login/password_reset.html', {'form': form})

# checks if the token is valid and redirects to reset password (no old password ) 
def forgot_password_change(request,uidb64,token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        myuser = CustomUser.objects.get(pk=uid)
    except (TypeError,ValueError,OverflowError,CustomUser.DoesNotExist):
        myuser = None

    if myuser is not None and generate_token.check_token(myuser,token):
        login(request,myuser)
        return redirect('password_change_no_old_pass')
    else:
        return redirect('signin')