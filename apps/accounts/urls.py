from django.urls import path
from .views import (
    RegisterView, LoginView, UserDetailView,
    UserProfileView, LogoutView, UpdateCurrencyView,
    UpdateProfileView, ChangePasswordView, UploadProfilePictureView,
    SubmitKYCView, KYCStatusView, NotificationPreferencesView,
    EnableTwoFactorView, VerifyTwoFactorView, DisableTwoFactorView
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', UserDetailView.as_view(), name='user-detail'),
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),
    path('auth/update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/upload-profile-picture/', UploadProfilePictureView.as_view(), name='upload-profile-picture'),
    path('auth/submit-kyc/', SubmitKYCView.as_view(), name='submit-kyc'),
    path('auth/kyc-status/', KYCStatusView.as_view(), name='kyc-status'),
    path('auth/notification-preferences/', NotificationPreferencesView.as_view(), name='notification-preferences'),
    path('auth/enable-2fa/', EnableTwoFactorView.as_view(), name='enable-2fa'),
    path('auth/verify-2fa/', VerifyTwoFactorView.as_view(), name='verify-2fa'),
    path('auth/disable-2fa/', DisableTwoFactorView.as_view(), name='disable-2fa'),
    path('auth/currency/', UpdateCurrencyView.as_view(), name='update-currency'),
]