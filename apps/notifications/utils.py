import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from ..companies.models import CompanyMember
from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger("create-notification")


def send_notifications(company_id: int, quiz_title: str, quiz_company_name: str) -> None:
    members = CompanyMember.objects.filter(company_id=company_id).select_related('user').only('user')
    channel_layer = get_channel_layer()

    for member in members:
        try:
            group_name = f"notifications_{member.user.id}"
            
            notification = Notification(
                user=member.user,
                text=f"New quiz '{quiz_title}' now available in company {quiz_company_name}!"
            )
            
            notification_data = NotificationSerializer(notification).data

            notification_message = {
                "type": "new_notification",
                "notification": notification_data,
            }

            async_to_sync(channel_layer.group_send)(
                group_name, notification_message
            )
            
            notification.save()
            
        except Exception as e:
            logger.error(f"Error sending notification for user {member.user}: {e}")
    