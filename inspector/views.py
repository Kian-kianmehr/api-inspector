
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Application, Specification
from .serializers import (
    ApplicationSerializer,
    SpecificationSerializer,
    AITestGenerationSerializer,
    AIResultAnalysisSerializer,
)

from .services.ai_client import (
    AIClient,
    AIServiceConnectionError,
    AIServiceResponseError,
)

from .services.openapi_converter import (
    OpenAPIConversionError,
    convert_openapi_to_ai_context,
)


# ============================================================
# Existing Application Views
# ============================================================

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


# ============================================================
# Existing Specification Views
# ============================================================

class SpecificationCreateView(generics.CreateAPIView):
    serializer_class = SpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        application = get_object_or_404(
            Application,
            pk=self.kwargs["application_id"],
            owner=self.request.user,
        )

        serializer.save(application=application)


class SpecificationListView(generics.ListAPIView):
    serializer_class = SpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Specification.objects.filter(
            application__owner=self.request.user,
            application_id=self.kwargs["application_id"],
        ).order_by("-created_at")


class SpecificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Specification.objects.filter(
            application__owner=self.request.user
        )


# ============================================================
# AI Security Helpers
# ============================================================

SENSITIVE_FIELD_NAMES = {
    "authorization",
    "proxy_authorization",
    "cookie",
    "cookies",
    "set_cookie",
    "password",
    "passwd",
    "secret",
    "client_secret",
    "api_key",
    "apikey",
    "access_key",
    "refresh_token",
    "access_token",
    "id_token",
    "token",
}


def sanitize_ai_data(value):
    """
    Recursively remove sensitive fields before sending
    test results to the AI service.
    """

    if isinstance(value, dict):
        sanitized = {}

        for key, item in value.items():
            normalized_key = (
                str(key)
                .strip()
                .lower()
                .replace("-", "_")
                .replace(" ", "_")
            )

            if normalized_key in SENSITIVE_FIELD_NAMES:
                continue

            if (
                normalized_key.endswith("_password")
                or normalized_key.endswith("_secret")
                or normalized_key.endswith("_token")
            ):
                continue

            sanitized[key] = sanitize_ai_data(item)

        return sanitized

    if isinstance(value, list):
        return [
            sanitize_ai_data(item)
            for item in value
        ]

    return value


# ============================================================
# AI Base View
# ============================================================

class BaseAISpecificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_specification(self):
        """
        Only allow access to specifications owned
        by the authenticated user.
        """

        return get_object_or_404(
            Specification.objects.select_related("application"),
            pk=self.kwargs["specification_id"],
            application__owner=self.request.user,
        )

    def get_api_context(self, specification):
        try:
            return convert_openapi_to_ai_context(
                specification.document,
                specification_name=specification.name,
            )

        except OpenAPIConversionError as error:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({
                "specification": str(error)
            })

    def get_ai_client(self):
        return AIClient()

    def handle_ai_error(self, error):
        if isinstance(error, AIServiceConnectionError):
            return Response(
                {
                    "detail": "The AI service is currently unavailable."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if isinstance(error, AIServiceResponseError):
            return Response(
                {
                    "detail": "The AI service returned an invalid response."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "detail": "An unexpected AI service error occurred."
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )


# ============================================================
# AI Test Generation
# ============================================================

class AITestGenerationView(BaseAISpecificationView):

    def post(self, request, specification_id):
        serializer = AITestGenerationSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        specification = self.get_specification()

        api_context = self.get_api_context(specification)

        instructions = serializer.validated_data["instructions"]

        try:
            result = self.get_ai_client().generate_tests(
                api_context=api_context,
                instructions=instructions,
            )

        except (
            AIServiceConnectionError,
            AIServiceResponseError,
        ) as error:
            return self.handle_ai_error(error)

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


# ============================================================
# AI Result Analysis
# ============================================================

class AIResultAnalysisView(BaseAISpecificationView):

    def post(self, request, specification_id):
        serializer = AIResultAnalysisSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        specification = self.get_specification()

        api_context = self.get_api_context(specification)

        test_results = sanitize_ai_data(
            serializer.validated_data["test_results"]
        )

        instructions = serializer.validated_data["instructions"]

        try:
            result = self.get_ai_client().analyze_results(
                api_context=api_context,
                test_results=test_results,
                instructions=instructions,
            )

        except (
            AIServiceConnectionError,
            AIServiceResponseError,
        ) as error:
            return self.handle_ai_error(error)

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
