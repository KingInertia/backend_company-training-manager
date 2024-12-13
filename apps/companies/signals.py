import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Company

logger = logging.getLogger("company_change")


@receiver(post_save, sender=Company)
def log_company_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Company created: {instance.name}, owned by {instance.owner.username}")
    else:
        logger.info(f"Company updated: {instance.name}, owned by {instance.owner.username}")


@receiver(post_delete, sender=Company)
def log_company_delete(sender, instance, **kwargs):
    logger.info(f"Company deleted: {instance.name}, owned by {instance.owner.username}")