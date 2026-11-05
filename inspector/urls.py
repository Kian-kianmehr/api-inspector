
from django.urls import path

from .views import (
    ApplicationCreateView,
    ApplicationListView,
    ApplicationDeleteView,
    SpecificationCreateView,
    SpecificationListView,
    SpecificationDetailView,
    AITestGenerationView,
    AIResultAnalysisView,
)


urlpatterns = [
    # Applications

    path(
        "applications/create/",
        ApplicationCreateView.as_view(),
        name="application-create",
    ),

    path(
        "applications/",
        ApplicationListView.as_view(),
        name="application-list",
    ),

    path(
        "applications/<int:pk>/delete/",
        ApplicationDeleteView.as_view(),
        name="application-delete",
    ),

    # Specifications

    path(
        "applications/<int:application_id>/specifications/create/",
        SpecificationCreateView.as_view(),
        name="specification-create",
    ),

    path(
        "applications/<int:application_id>/specifications/",
        SpecificationListView.as_view(),
        name="specification-list",
    ),

    path(
        "specifications/<int:pk>/",
        SpecificationDetailView.as_view(),
        name="specification-detail",
    ),

    # AI

    path(
        "specifications/<int:specification_id>/ai/generate-tests/",
        AITestGenerationView.as_view(),
        name="ai-test-generation",
    ),

    path(
        "specifications/<int:specification_id>/ai/analyze-results/",
        AIResultAnalysisView.as_view(),
        name="ai-result-analysis",
    ),
]
