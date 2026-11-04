from django.db import models
from django.conf import settings


class Application(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications"
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Application"
        verbose_name_plural = "Applications"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_application_name_per_owner"
            )
        ]

    def __str__(self):
        return self.name


class Specification(models.Model):
    application = models.ForeignKey(Application,on_delete=models.CASCADE,related_name="specifications")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    api_version = models.CharField(max_length=100)
    openapi_version = models.CharField(max_length=20)
    document = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Specification"
        verbose_name_plural = "Specifications"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "name"],
                name="unique_specification_name_per_application"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.api_version})"