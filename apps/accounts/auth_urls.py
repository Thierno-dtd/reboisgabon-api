from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import auth_views as views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('login/2fa/verify/', views.TwoFAVerifyView.as_view(), name='login-2fa-verify'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    path('password/forgot/', views.ForgotPasswordView.as_view(), name='password-forgot'),
    path('password/reset/', views.ResetPasswordView.as_view(), name='password-reset'),

    path('2fa/setup/init/', views.TOTPSetupInitView.as_view(), name='2fa-setup-init'),
    path('2fa/setup/confirm/', views.TOTPSetupConfirmView.as_view(), name='2fa-setup-confirm'),
    path('2fa/disable/', views.TOTPDisableView.as_view(), name='2fa-disable'),

    path('me/', views.MeView.as_view(), name='me'),
]