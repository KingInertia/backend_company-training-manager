from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import NotificationSerializer


def send_notifications(notifications):
    channel_layer = get_channel_layer()
    for n in notifications:
        group_name = f"notifications_{n.user.id}"

        notification_data = NotificationSerializer(n).data

        notification = {
                "type": "new_notification",
                "notification": notification_data,
            }

        async_to_sync(channel_layer.group_send)(
            group_name, notification

        )
        
        

