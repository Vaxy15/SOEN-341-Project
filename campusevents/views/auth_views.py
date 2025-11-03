# campusevents/views/auth_views.py
"""
Authentication and registration views.
"""

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from ..models import User
from ..serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    StudentRegistrationSerializer,
    OrganizerRegistrationSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view that includes user role information."""
    serializer_class = CustomTokenObtainPairSerializer


class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data.get("password"))
            user.save()
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            return Response(
                {"access": str(access_token), "refresh": str(refresh), "user": UserSerializer(user).data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data.get("password"))
            user.save()
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            return Response(
                {
                    "message": "Student registration successful",
                    "access": str(access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                        "is_active": user.is_active,
                        "is_verified": user.is_verified,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizerRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OrganizerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data.get("password"))
            user.role = User.ROLE_ORGANIZER
            # Require approval:
            user.is_active = False
            user.is_verified = False
            user.save()
            return Response(
                {
                    "message": "Organizer registration submitted. Pending admin approval.",
                    "status": "pending_approval",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                        "is_active": user.is_active,
                        "is_verified": user.is_verified,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.method == "POST":
        role = (request.POST.get("role") or "").strip().lower()

        payload = {
            "email": (request.POST.get("email") or "").strip(),
            "password": request.POST.get("password") or "",
            "password_confirm": request.POST.get("password_confirm") or "",
            "first_name": (request.POST.get("first_name") or "").strip(),
            "last_name": (request.POST.get("last_name") or "").strip(),
            "student_id": (request.POST.get("student_id") or "").strip(),
            "phone_number": (request.POST.get("phone_number") or "").strip(),
        }

        # Pick the right serializer based on role
        if role == User.ROLE_STUDENT:
            serializer = StudentRegistrationSerializer(data=payload)
            role_label = "Student"
        elif role == User.ROLE_ORGANIZER:
            serializer = OrganizerRegistrationSerializer(data=payload)
            role_label = "Event Organizer"
        else:
            messages.error(request, "Please choose a valid account type (Student or Organizer).")
            return render(request, "register.html", {"form": request.POST}, status=400)

        if serializer.is_valid():
            user = serializer.save()
            user.set_password(payload["password"])
            user.role = role

            if role == User.ROLE_STUDENT:
                # Students: usable immediately
                user.is_active = True
                user.is_verified = True
                success_msg = f"{role_label} account created! You can sign in now."
            else:
                # Organizers: require admin approval
                user.is_active = False
                user.is_verified = True
                success_msg = (
                    f"{role_label} registration submitted. "
                    "An administrator must approve your account before you can sign in."
                )

            user.save()
            messages.success(request, success_msg)
            return redirect("login")

        # Validation errors
        return render(
            request,
            "register.html",
            {"form": request.POST, "errors": serializer.errors},
            status=400,
        )

    # GET
    return render(request, "register.html")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
    except KeyError:
        return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

