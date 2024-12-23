import logging

from ..companies.models import CompanyMember
from .models import Notification

logger = logging.getLogger("create-notification")


def send_notifications(company_id: int, quiz_title: str, quiz_company_name: str) -> None:
    members = CompanyMember.objects.filter(company_id=company_id).select_related('user').only('user')

    for member in members:
        try:
            notification = Notification(
                user=member.user,
                text=f"New quiz '{quiz_title}' now available in company {quiz_company_name}!"
            )
            notification.save()
            
        except Exception as e:
            logger.error(f"Error while creating and saving notification for user {member.user}: {e}")
    