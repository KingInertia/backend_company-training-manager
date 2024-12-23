import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger("create-notification")


@receiver(post_save, sender=Notification)
def send_notification_to_user(sender, instance, created, **kwargs):
    if created:
        try:
            channel_layer = get_channel_layer()
            group_name = f"notifications_{instance.user.id}"

            notification_data = NotificationSerializer(instance).data

            notification_message = {
                "type": "new_notification",
                "notification": notification_data,
            }

            async_to_sync(channel_layer.group_send)(
                group_name, notification_message
            )

        except Exception as e:
            logger.error(f"Error sending notification for user {instance.user.id}: {e}")