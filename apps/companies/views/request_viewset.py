from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import CompanyMember, CompanyRequest
from ..permission import IsOwnerOfCompany
from ..serializers import CompanyRequestSerializer


class CompanyRequestViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CompanyRequest.objects.filter(receiver=user)

    @action(detail=True, methods=['patch'], url_path='approve', permission_classes=[IsOwnerOfCompany])
    def approve_request(self, request, *args, **kwargs):
        request_obj = self.get_object()

        if request_obj.status != CompanyRequest.RequestState.PENDING:
            return Response({"detail": "Request already processed."}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.status = CompanyRequest.RequestState.APPROVED
        request_obj.save()

        CompanyMember.objects.create(
            user=request_obj.sender,
            company=request_obj.company,
            role=CompanyMember.Role.MEMBER
        )

        return Response(CompanyRequestSerializer(request_obj).data)

    @action(detail=True, methods=['patch'], url_path='reject', permission_classes=[IsOwnerOfCompany])
    def reject_request(self, request, *args, **kwargs):
        request_obj = self.get_object()

        if request_obj.status != CompanyRequest.RequestState.PENDING:
            return Response({"detail": "Request already processed."}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.status = CompanyRequest.RequestState.REJECTED
        request_obj.save()

        return Response(CompanyRequestSerializer(request_obj).data)

    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel_request(self, request, *args, **kwargs):
        request_id = kwargs.get('pk')
        
        try:
            request_obj = CompanyRequest.objects.get(id=request_id)
        except CompanyRequest.DoesNotExist:
            return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if request_obj.sender != request.user:
            return Response({"detail": "You are not the sender of this request."}, status=status.HTTP_403_FORBIDDEN)
        
        if request_obj.status != CompanyRequest.RequestState.PENDING:
            return Response({"detail": "Request already processed."}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.status = CompanyRequest.RequestState.CANCELLED
        request_obj.save()

        return Response(CompanyRequestSerializer(request_obj).data)

    @action(detail=False, methods=['get'], url_path='user-requests')
    def list_user_requests(self, request, *args, **kwargs):
        requests = CompanyRequest.objects.filter(sender=request.user)
        return Response(CompanyRequestSerializer(requests, many=True).data)
    
    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied()