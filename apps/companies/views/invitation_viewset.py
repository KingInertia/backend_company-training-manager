from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import CompanyInvitation, CompanyMember
from ..permission import IsOwnerOfCompany
from ..serializers import CompanyInvitationSerializer


class CompanyInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CompanyInvitation.objects.filter(sender=user)

    @action(detail=True, methods=['patch'], url_path='accept')
    def accept_invitation(self, request, *args, **kwargs):
        invitation_id = kwargs.get('pk')
        
        try:
            invitation = CompanyInvitation.objects.get(id=invitation_id)
        except CompanyInvitation.DoesNotExist:
            return Response({"detail": "Invitation not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if invitation.receiver != request.user:
            return Response(
                {"detail": "You are not the receiver of this invitation."},
                status=status.HTTP_403_FORBIDDEN
                )        
        
        if invitation.status != CompanyInvitation.InvitationState.PENDING:
            return Response({"detail": "Invitation already processed."}, status=status.HTTP_400_BAD_REQUEST)

        invitation.status = CompanyInvitation.InvitationState.ACCEPTED
        invitation.save()

        CompanyMember.objects.create(
            user=request.user,
            company=invitation.company,
            role=CompanyMember.Role.MEMBER
        )

        return Response(CompanyInvitationSerializer(invitation).data)

    @action(detail=True, methods=['patch'], url_path='decline')
    def decline_invitation(self, request, *args, **kwargs):
        invitation_id = kwargs.get('pk')
        
        try:
            invitation = CompanyInvitation.objects.get(id=invitation_id)
        except CompanyInvitation.DoesNotExist:
            return Response(
                {"detail": "Invitation not found."},
                status=status.HTTP_404_NOT_FOUND
                )

        if invitation.receiver != request.user:
            return Response(
                {"detail": "You are not the receiver of this invitation."},
                status=status.HTTP_403_FORBIDDEN
                )

        if invitation.status != CompanyInvitation.InvitationState.PENDING:
            return Response({"detail": "Invitation already processed."}, status=status.HTTP_400_BAD_REQUEST)

        invitation.status = CompanyInvitation.InvitationState.DECLINED
        invitation.save()

        return Response(CompanyInvitationSerializer(invitation).data)

    @action(detail=True, methods=['patch'], url_path='revoke', permission_classes=[IsOwnerOfCompany])
    def revoke_invitation(self, request, *args, **kwargs):
        invitation = self.get_object()
        
        if invitation.status != CompanyInvitation.InvitationState.PENDING:
            return Response({"detail": "Invitation already processed."}, status=status.HTTP_400_BAD_REQUEST)

        invitation.status = CompanyInvitation.InvitationState.REVOKED
        invitation.save()

        return Response(CompanyInvitationSerializer(invitation).data)

    @action(detail=False, methods=['get'], url_path='user-invitations')
    def list_user_invitations(self, request, *args, **kwargs):
        invitations = CompanyInvitation.objects.filter(receiver=request.user)
        return Response(CompanyInvitationSerializer(invitations, many=True).data)
    
    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Deletion of invitations is not allowed.")