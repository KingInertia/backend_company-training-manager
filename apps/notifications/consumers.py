import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Notification
from .serializers import NotificationSerializer


class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        query_string = self.scope['query_string'].decode('utf-8')
        
        token = None
        if "token=" in query_string:
            token = query_string.split("token=")[1]
        if token:
            try:
                validated_token = JWTAuthentication().get_validated_token(token)
                user = JWTAuthentication().get_user(validated_token)
                self.user = user
            except Exception:
                self.user = AnonymousUser() 
        else:
            self.user = AnonymousUser()

        if not self.user.is_authenticated:
            self.close()
            return
        
        self.group_name = f"notifications_{self.user.pk}"
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

        user_notifications = Notification.objects.filter(
            user=self.user.pk,
            )

        notification_data = NotificationSerializer(user_notifications, many=True).data
        self.send(text_data=json.dumps({
            "type": "notification_list",
            "notifications": notification_data
            }))

    def disconnect(self, close_code):

        if self.user.is_authenticated:
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name
            )
            
    def new_notification(self, notification):
        notification_data = notification["notification"]
        self.send(text_data=json.dumps({
            "type": "new_notification",
            "notification": notification_data
        }))
    
    def receive(self, text_data):
        if not self.user.is_authenticated:
            self.close()
            return
        
        data = json.loads(text_data)
        
        notification_id = data.get("notification_id")
        if notification_id:
            try:
                notification = Notification.objects.get(id=notification_id, user=self.user.pk)
                notification.status = Notification.Status.READ
                notification.save()

                self.send(text_data=json.dumps({
                    "type": "change_status",
                    "status": "read",
                    "notification_id": notification_id,
                }))
            except Notification.DoesNotExist:
                self.send(text_data=json.dumps({
                    "type": "change_status",
                    "status": "unread",
                    "message": "Notification not found."
                }))
    