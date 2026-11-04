from django.urls import path

from .views import (
    ApplicationCreateView,
    ApplicationListView,
    ApplicationDeleteView,
    SpecificationCreateView,
    SpecificationListView,
    SpecificationDetailView,
)


urlpatterns = [
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
]