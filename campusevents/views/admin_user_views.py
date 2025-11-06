# campusevents/views/admin_user_views.py
"""
Admin views for user management, approval, and moderation.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import User
from ..serializers import (
    AdminUserSerializer,
    UserApprovalSerializer,
    UserRoleUpdateSerializer,
    UserStatusUpdateSerializer,
)
from .utils import EventPagination


class AdminUserManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can manage users"}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all()
        role_filter = request.query_params.get("role")
        status_filter = request.query_params.get("status")
        search = request.query_params.get("search")
        verification_status = request.query_params.get("verification_status")

        if role_filter:
            users = users.filter(role=role_filter)
        if status_filter == "active":
            users = users.filter(is_active=True)
        elif status_filter == "inactive":
            users = users.filter(is_active=False)
        if verification_status == "verified":
            users = users.filter(is_verified=True)
        elif verification_status == "unverified":
            users = users.filter(is_verified=False)
        if search:
            users = users.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(student_id__icontains=search)
            )

        users = users.order_by("-created_at")
        paginator = EventPagination()
        page = paginator.paginate_queryset(users, request)
        if page is not None:
            return paginator.get_paginated_response(AdminUserSerializer(page, many=True).data)
        return Response(AdminUserSerializer(users, many=True).data)


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can view user details"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserSerializer(user).data)

    def patch(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can update users"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can approve/reject users"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserApprovalSerializer(data=request.data)
        if serializer.is_valid():
            action = serializer.validated_data["action"]
            reason = serializer.validated_data.get("reason", "")
            if action == "approve":
                user.is_verified = True
                user.is_active = True
                user.save()
                message = f"User {user.email} has been approved successfully."
            else:
                user.is_verified = False
                user.is_active = False
                user.save()
                message = f"User {user.email} has been rejected."
            return Response({"message": message, "user": AdminUserSerializer(user).data, "reason": reason}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can change user roles"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserRoleUpdateSerializer(data=request.data)
        if serializer.is_valid():
            old_role = user.role
            user.role = serializer.validated_data["role"]
            user.save()
            return Response({"message": f"User role changed from {old_role} to {user.role}", "user": AdminUserSerializer(user).data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        if not request.user.is_admin():
            return Response({"error": "Only administrators can change user status"}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object(pk)
        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            user.is_active = serializer.validated_data["is_active"]
            user.is_verified = serializer.validated_data.get("is_verified", user.is_verified)
            user.save()
            status_text = "activated" if user.is_active else "deactivated"
            return Response({"message": f"User {user.email} has been {status_text}", "user": AdminUserSerializer(user).data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminPendingOrganizersView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = EventPagination

    def get(self, request):
        if not request.user.is_admin():
            return Response(
                {"error": "Only administrators can view pending organizers"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get unverified organizers
        pending_organizers = User.objects.filter(
            role=User.ROLE_ORGANIZER, is_verified=False
        ).order_by("-created_at")

        # Apply search filter
        search = request.query_params.get("search")
        if search:
            pending_organizers = pending_organizers.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        # Paginate results
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(pending_organizers, request)

        serializer = AdminUserSerializer(page or pending_organizers, many=True)

        if page is not None:
            return paginator.get_paginated_response(serializer.data)

        return Response(serializer.data)


@login_required(login_url='login')
def admin_users_dashboard(request):
    """
    Simple HTML page for administrators to list users and perform basic actions:
    - Change role (student / organizer / admin)
    - Toggle active status
    """
    if not getattr(request.user, 'is_admin', lambda: False)():
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Only administrators can view this page")

    users = User.objects.all().order_by('-created_at')[:200]
    return render(request, "admin_users_dashboard.html", {"users": users})

