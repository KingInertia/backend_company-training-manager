from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(user=user)
    
    @action(detail=False, methods=['patch'], url_path='mark-as-read')
    def mark_as_read(self, request):
        notification_id = request.query_params.get('notification_id')

        if not notification_id:
            return Response({"detail": "Notification ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        updated_count = Notification.objects.filter(
            id=notification_id, user=user, status=Notification.Status.UNREAD
        ).update(status=Notification.Status.READ)

        if updated_count == 0:
            return Response(
                {"detail": "Notification not found or already marked as read."},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Notification marked as read."}, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        raise PermissionDenied("You cannot create a notification directly.")

    def update(self, request, *args, **kwargs):
        raise PermissionDenied("You cannot update a notification directly.")

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied("You cannot partially update a notification directly.")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("You cannot delete a notification directly.")
    