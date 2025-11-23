# campusevents/permissions.py

from rest_framework import permissions


class IsStudent(permissions.BasePermission):
    """Permission class to check if user is a student."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'student'
        )


class IsOrganizer(permissions.BasePermission):
    """Permission class to check if user is an organizer."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'organizer'
        )


class IsAdmin(permissions.BasePermission):
    """Permission class to check if user is an admin."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsOrganizerOrAdmin(permissions.BasePermission):
    """Permission class to check if user is an organizer or admin."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['organizer', 'admin']
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permission class to allow owners to edit their own objects."""

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for the owner
        return obj.created_by == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """Permission class to allow only admins to edit, others can read."""

    def has_permission(self, request, view):
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions only for admins
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )
