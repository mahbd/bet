from django.db import models


class Logging(models.Model):
    error_type = models.CharField(max_length=255)
    error_message = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
