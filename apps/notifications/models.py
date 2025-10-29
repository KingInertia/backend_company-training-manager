from django.conf import settings
from django.db import models

from tools.models import TimeStampedModel


class Notification(TimeStampedModel):
    class Status(models.TextChoices):
        UNREAD = 'unread', 'Unread'
        READ = 'read', 'Read'
    text = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNREAD)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.text[:20]}"