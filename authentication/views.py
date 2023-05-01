from django.shortcuts import render, redirect
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from validate_email import validate_email
from django.contrib import messages
# from django.core.mail import EmailMessage
from email.message import EmailMessage
import smtplib
from django.urls import reverse
from django.utils.encoding import force_bytes, DjangoUnicodeDecodeError, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
# from .utils import token_generator
from django.contrib import auth
from .utils import account_activation_token
from django.contrib.auth.tokens import PasswordResetTokenGenerator
import threading

# Create your views here.


class EmailThread(threading.Thread):
    def __init__(self, email):

        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.ehlo()
        s.starttls()
        s.login("homefactory.xxx.com", "xxxxxxxxx")
        s.send_message(self.email)


class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        if not validate_email(email):
            return JsonResponse({'email_error': 'email is inavalid'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'email_error': 'email is used, choose another one'}, status=400)
        return JsonResponse({'email_valid': True})


class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            return JsonResponse({'username_error': 'username should only contain alphanumeric chars'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'username_error': 'username is used, choose another one'}, status=400)
        return JsonResponse({'username_valid': True})


class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if not account_activation_token.check_token(user, token):
                return redirect('login'+'?message='+'User is already activted')

            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.save()
            messages.success(request, 'Account activated successfully')
            return redirect('login')
        except Exception as ex:
            pass
        return redirect('login')


class LoginView(View):
    def get(self, request):
        return render(request, 'authentication/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        if username and password:
            user = auth.authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    auth.login(request, user)
                    messages.success(request, "Welcome, " +
                                     user.username + 'You are now logged in')
                    return redirect('expenses')
                messages.error(
                    request, "Account is not active please  check your email")
                return render(request, 'authentication/login.html')

            messages.error(request, "Invalid creds try again")
            return render(request, 'authentication/login.html')

        messages.error(request, "Please provid the username and password")
        return render(request, 'authentication/login.html')


class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):
        # GET USER DATA
        # VALIDATE
        # create a user account

        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        context = {
            'fieldValues': request.POST
        }

        if not User.objects.filter(username=username).exists():
            if not User.objects.filter(email=email).exists():
                if len(password) < 6:
                    messages.error(request, 'Password too short')
                    return render(request, 'authentication/register.html', context)

                user = User.objects.create_user(username=username, email=email)
                user.set_password(password)
                user.is_active = False
                user.save()
                current_site = get_current_site(request)
                email_body = {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                }

                link = reverse('activate', kwargs={
                               'uidb64': email_body['uid'], 'token': email_body['token']})

                email_subject = 'Activate your account'

                activate_url = 'http://'+current_site.domain+link
                email_msg = 'Hi ' + user.username + \
                    ', \n please uset this link to verify your account\n' + activate_url
                msg = EmailMessage()
                msg.set_content(email_msg)
                msg['Subject'] = f'The contents of {email_subject}'
                msg['From'] = "homefactory.xxxxxx.com"
                msg['To'] = email
                EmailThread(msg).start()
                messages.success(request, 'Account successfully created')
                return render(request, 'authentication/register.html')

        return render(request, 'authentication/register.html')


class LogoutView(View):
    def post(self, request):
        # import pdb
        # pdb.set_trace()
        auth.logout(request)
        messages.success(request, "You have been logged out.")
        return redirect('login')


class RequestPasswordResetEmail(View):

    def get(self, request):
        return render(request, 'authentication/reset-password.html')

    def post(self, request):
        context = {
            'values': request.POST
        }
        email = request.POST['email']
        if not validate_email(email):
            messages.error(request, "Please provide a vaild email")
            return render(request, 'authentication/reset-password.html', context)

        user = User.objects.filter(email=email)
        if user.exists():
            current_site = get_current_site(request)
            email_contents = {
                'user': user[0],
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
                'token': PasswordResetTokenGenerator().make_token(user[0]),
            }

            link = reverse('reset-user-password', kwargs={
                'uidb64': email_contents['uid'], 'token': email_contents['token']})

            email_subject = 'Reset Password'

            reset_url = 'http://'+current_site.domain+link
            email_msg = 'Hi there,\n\n please click the link below to reset your password \n' + reset_url
            msg = EmailMessage()
            msg.set_content(email_msg)
            msg['Subject'] = f'The contents of {email_subject}'
            msg['From'] = "homefactory.xxxxxxxx.com"
            msg['To'] = email
            EmailThread(msg).start()
        messages.success(
            request, "We have sent you an email to reset password")

        return render(request, 'authentication/reset-password.html')


class CompletePasswordReset(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                messages.info(request,
                              "Password link is invalid please request a new one")
                return render(request, 'authentication/reset-password.html')

            # messages.success(request, "Password updated successfully!!")
            # return redirect('login')
        except Exception as e:
            # import pdb
            # pdb.set_trace()
            pass
        return render(request, 'authentication/set-new-password.html', context)

    def post(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        # import pdb
        # pdb.set_trace()
        password = request.POST['password']
        password2 = request.POST['password2']
        if password != password2:
            messages.error('passwords do not match')
            return render(request, 'authentication/set-new-password.html', context)
        if len(password) < 6:
            messages.error(request, "Password is too shot!")
            return render(request, 'authentication/set-new-password.html', context)
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            user.set_password(password)
            user.save()
            messages.success(request, "Password updated successfully!!")
            return redirect('login')

        except Exception as e:
            # import pdb
            # pdb.set_trace()
            messages.info(request, "Something went wrong, try again")
            return render(request, 'authentication/set-new-password.html', context)
