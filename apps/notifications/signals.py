# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
# from .models import Notification
# from .serializers import NotificationSerializer

# @receiver(post_save, sender=Notification)
# def send_notification_to_user(sender, instance, created, **kwargs):
#     print(1)
#     if created:
#         channel_layer = get_channel_layer()
#         group_name = f"notifications_{instance.user.id}"
#         print(group_name)
#         print(channel_layer)

#         notification_data = NotificationSerializer(instance).data
#         print(notification_data)

#         async_to_sync(channel_layer.group_send)(
#             group_name,
#             {
#                 "type": "notify",
#                 "notifications": notification_data,
#             }
#         )
