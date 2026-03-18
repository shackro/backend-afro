from decimal import Decimal
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.files.storage import default_storage
from django.conf import settings
import pyotp
import qrcode
import io
import base64
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    TokenResponseSerializer, UserProfileSerializer, UpdateProfileSerializer,
    ChangePasswordSerializer, KYCSerializer, NotificationPreferencesSerializer,
    TwoFactorSerializer, UpdateCurrencySerializer
)
from .models import UserProfile

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Get referral code from request
        referral_code = request.data.get('referral_code', '')

        # Process sign-up bonus if referral code was provided
        if referral_code:
            try:
                referrer = User.objects.get(referral_code=referral_code)
                user.referred_by = referrer
                user.save()

                # Update the team tree
                from apps.team.utils import update_team_tree
                update_team_tree(user, referrer)

                # 🎁 GIVE $1 SIGN-UP BONUS TO REFERRER
                from apps.transactions.models import Transaction
                from django.utils import timezone
                import uuid

                # Add $1 to referrer's balance
                referrer.balance += Decimal('1.00')

                # Update bonus tracking fields if they exist
                if hasattr(referrer, 'total_bonus_earned'):
                    referrer.total_bonus_earned += Decimal('1.00')
                if hasattr(referrer, 'bonus_count'):
                    referrer.bonus_count += 1

                referrer.save()

                # Create a transaction record for the bonus
                Transaction.objects.create(
                    user=referrer,
                    transaction_type='deposit',
                    amount=Decimal('1.00'),
                    currency='USD',
                    status='completed',
                    payment_method='referral_bonus',
                    reference=f"BONUS-{uuid.uuid4().hex[:8].upper()}",
                    description=f"Sign-up bonus for referring {user.email}",
                    completed_at=timezone.now()
                )

                print(f"🎁 $1 sign-up bonus given to {referrer.email} for referring {user.email}")

            except User.DoesNotExist:
                # Invalid referral code - just continue without linking
                pass
            except Exception as e:
                print(f"Error processing referral bonus: {e}")

        # Create user profile
        UserProfile.objects.get_or_create(user=user)

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UpdateProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        user = request.user
        serializer = UpdateProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['current_password']):
                return Response(
                    {"current_password": "Wrong password."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(serializer.validated_data['new_password'])
            user.save()
            update_session_auth_hash(request, user)

            return Response({"message": "Password updated successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadProfilePictureView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if 'profile_picture' not in request.FILES:
            return Response(
                {"error": "No image provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile, created = UserProfile.objects.get_or_create(user=request.user)

        # Delete old profile picture if exists
        if profile.profile_picture:
            default_storage.delete(profile.profile_picture.path)

        profile.profile_picture = request.FILES['profile_picture']
        profile.save()

        return Response({
            "profile_picture": profile.profile_picture.url,
            "message": "Profile picture updated successfully"
        })


class SubmitKYCView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = KYCSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user

            # Store KYC documents (you might want to create a KYC model)
            # For now, just update user fields
            user.id_document_type = serializer.validated_data['id_type']
            user.id_document = serializer.validated_data['front_image']
            # Store other documents in a KYC model
            user.is_kyc_verified = False  # Set to pending
            user.save()

            return Response({
                "status": "pending",
                "message": "KYC documents submitted successfully"
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KYCStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_kyc_verified:
            status = "verified"
        elif user.id_document:  # Has submitted documents but not verified
            status = "pending"
        else:
            status = "not_submitted"

        return Response({"status": status})


class NotificationPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        return Response({"preferences": profile.notification_preferences})

    def patch(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = NotificationPreferencesSerializer(
            profile,
            data={"notification_preferences": request.data},
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"preferences": profile.notification_preferences})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EnableTwoFactorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)

        # Generate secret
        secret = pyotp.random_base32()
        profile.two_factor_secret = secret
        profile.save()

        # Generate QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            request.user.email,
            issuer_name="Afro Connect"
        )

        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            "qr_code": f"data:image/png;base64,{qr_code}",
            "secret": secret
        })


class VerifyTwoFactorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TwoFactorSerializer(data=request.data)
        if serializer.is_valid():
            profile = request.user.profile
            if not profile.two_factor_secret:
                return Response(
                    {"error": "2FA not enabled"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            totp = pyotp.TOTP(profile.two_factor_secret)
            if totp.verify(serializer.validated_data['code']):
                profile.two_factor_enabled = True
                profile.save()
                return Response({"message": "2FA enabled successfully"})

            return Response(
                {"error": "Invalid code"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DisableTwoFactorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        profile.two_factor_enabled = False
        profile.two_factor_secret = None
        profile.save()
        return Response({"message": "2FA disabled successfully"})


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class UpdateCurrencyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UpdateCurrencySerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.preferred_currency = serializer.validated_data['preferred_currency']
            user.save()
            return Response({
                'status': 'success',
                'preferred_currency': user.preferred_currency,
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)