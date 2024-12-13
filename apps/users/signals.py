import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

User = settings.AUTH_USER_MODEL
logger = logging.getLogger("user_change")


@receiver(post_save, sender=User)
def log_user_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"User created: {instance.username}")
    else:
        logger.info(f"User updated: {instance.username}")


@receiver(post_delete, sender=User)
def log_user_delete(sender, instance, **kwargs):
    logger.info(f"User deleted: {instance.username}")


