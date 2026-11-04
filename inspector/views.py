
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions

from .models import Application, Specification
from .serializers import ApplicationSerializer, SpecificationSerializer


class ApplicationCreateView(generics.CreateAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ApplicationListView(generics.ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(
            owner=self.request.user
        ).order_by("-created_at")


class ApplicationDeleteView(generics.DestroyAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(
            owner=self.request.user
        )


class SpecificationCreateView(generics.CreateAPIView):
    serializer_class = SpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        application = get_object_or_404(
            Application,
            pk=self.kwargs["application_id"],
            owner=self.request.user
        )
        serializer.save(application=application)


class SpecificationListView(generics.ListAPIView):
    serializer_class = SpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Specification.objects.filter(
            application__owner=self.request.user,
            application_id=self.kwargs["application_id"]
        ).order_by("-created_at")


class SpecificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Specification.objects.filter(
            application__owner=self.request.user
        )
