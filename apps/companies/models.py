from django.conf import settings
from django.db import models

from tools.models import TimeStampedModel


class Company(TimeStampedModel):
    VISIBILITY_CHOICES = [
        ('hidden', 'hidden'),
        ('visible', 'visible'),
    ]
    name = models.CharField(max_length=50)
    description = models.TextField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='companies',
        on_delete=models.CASCADE)
    visibility = models.CharField(
        max_length=7,
        choices=VISIBILITY_CHOICES,
        default='visible'
    
    )
    class Meta:
        verbose_name_plural = "Companies"