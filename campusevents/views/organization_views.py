# campusevents/views/organization_views.py
"""
Organization management views.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Organization
from ..api.serializers import OrganizationSerializer


class OrganizationListView(APIView):
    """List all organizations and allow admins to create new ones."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orgs = Organization.objects.all()
        serializer = OrganizationSerializer(orgs, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Only administrators can create organizations
        if not getattr(request.user, "role", None) == "admin":
            return Response(
                {"error": "Only administrators can create organizations"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrganizationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

