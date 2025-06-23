#Librerías para QR
import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64

#Librerías para Auth
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.contrib.auth.models import User

#Modelo de la APP con el OTP (One time Password)
from .models import UserOTP

# Create your views here.

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return render(request, 'register.html')

        # Crear usuario
        user = User.objects.create_user(username=username, password=password)
        user.save()

        # Generar clave secreta TOTP automáticamente
        otp_secret = pyotp.random_base32()
        UserOTP.objects.create(user=user, otp_secret=otp_secret)

        messages.success(request, 'Usuario registrado exitosamente. Por favor inicia sesión.')
        return redirect('login')

    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            request.session['pre_2fa_user'] = user.id  # Guarda usuario temporal
            return redirect('verify')
        else:
            messages.error(request, 'Credenciales incorrectas.')

    return render(request, 'login.html')

def verify_code(request):
    user_id = request.session.get('pre_2fa_user')
    if user_id is None:
        return redirect('login')

    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)

    try:
        user_otp = UserOTP.objects.get(user=user)
    except UserOTP.DoesNotExist:
        otp_secret = pyotp.random_base32()
        user_otp = UserOTP.objects.create(user=user, otp_secret=otp_secret)

    otp_uri = pyotp.totp.TOTP(user_otp.otp_secret).provisioning_uri(
        name=user.username, issuer_name="SeguridadMGTI"
    )
    qr = qrcode.make(otp_uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    if request.method == 'POST':
        code = request.POST.get('code')
        totp = pyotp.TOTP(user_otp.otp_secret)
        if totp.verify(code):
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Código incorrecto.')

    return render(request, 'verify.html', {'qr_base64': qr_base64})

@login_required
def dashboard(request):
    return render(request, 'dashboard.html', {'user': request.user})

def regenerate_qr(request):
    user_id = request.session.get('pre_2fa_user')
    if not user_id:
        return redirect('login')  # Si no hay sesión parcial, volvemos al login

    from django.contrib.auth.models import User
    user = User.objects.get(id=user_id)

    try:
        user_otp = UserOTP.objects.get(user=user)
    except UserOTP.DoesNotExist:
        user_otp = UserOTP.objects.create(user=user, otp_secret=pyotp.random_base32())

    new_secret = pyotp.random_base32()
    user_otp.otp_secret = new_secret
    user_otp.save()

    messages.success(request, 'QR regenerado. Escanéalo en Google Authenticator.')
    return redirect('verify')  # Volvemos a la verificación MFA para que vea el nuevo QR