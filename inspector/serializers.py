from rest_framework import serializers

from .models import Application, Specification


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class SpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specification
        fields = [
            "id",
            "application",
            "name",
            "description",
            "api_version",
            "openapi_version",
            "document",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "application",
            "created_at",
            "updated_at",
        ]