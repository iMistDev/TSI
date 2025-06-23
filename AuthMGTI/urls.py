from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify/', views.verify_code, name='verify'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('regenerate_qr/', views.regenerate_qr, name='regenerate_qr'),
]
