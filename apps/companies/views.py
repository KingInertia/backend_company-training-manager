from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Company, CompanyInvitation, CompanyMember, CompanyRequest
from .permission import IsMemberOfCompany, IsOwner, IsOwnerOfCompany
from .serializers import (
    CompanyInvitationSerializer,
    CompanyListSerializer,
    CompanyMemberSerializer,
    CompanyRequestSerializer,
    CompanySerializer,
)


class CompanyViewSet(viewsets.ModelViewSet):
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated, IsOwner] 
    
    def get_serializer_class(self):       
        if self.action == 'list':
            return CompanyListSerializer
        return CompanySerializer    
    
    def perform_create(self, serializer):
        company = serializer.save(owner=self.request.user)    
        
        CompanyMember.objects.create(
            user=self.request.user,
            company=company,
            role=CompanyMember.Role.OWNER 
        )
        
    def get_queryset(self):
        user = self.request.user
        user_memberships = CompanyMember.objects.filter(user=user)
        company_ids = user_memberships.values_list('company', flat=True)
        companies = Company.objects.filter(
            Q(owner=user) | 
            Q(visibility=Company.Visibility.VISIBLE) | 
            Q(id__in=company_ids)
        )

        return companies    


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
        except CompanyRequest.DoesNotExist:
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

    @action(detail=True, methods=['patch'], url_path='cancelled')
    def cancelled_request(self, request, *args, **kwargs):
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
    
    

class CompanyMemberViewSet(viewsets.ModelViewSet):
    queryset = CompanyMember.objects.all()
    serializer_class = CompanyMemberSerializer
    permission_classes = [IsAuthenticated]
    

    def get_permissions(self):
        if self.action == 'leave_company':
            return [IsMemberOfCompany()]
        elif self.action == 'kick_from_company':
            return [IsOwnerOfCompany()]
        return super().get_permissions()

    @action(detail=False, methods=['delete'], url_path='leave')
    def leave_company(self, request):
        company_id = request.data.get('company')

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
                            
        if company.owner.id == request.user:
            return Response({"detail": "Owner cannot leave the company."}, status=status.HTTP_403_FORBIDDEN)       

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            membership = CompanyMember.objects.get(user=request.user, company=company_id)
            membership.delete()
            return Response({"detail": "You have successfully left the company."}, status=status.HTTP_200_OK)
        except CompanyMember.DoesNotExist:
            raise PermissionDenied()

    @action(detail=False, methods=['delete'], url_path='kick')
    def kick_from_company(self, request):
        company_id = request.data.get('company')
        user_id = request.data.get('user')  
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        if company.owner.id == user_id:
            return Response({"detail": "You cannot kick the owner of the company."}, status=status.HTTP_403_FORBIDDEN)

        if not company_id or not user_id:
            return Response({"detail": "Company ID and User ID are required."}, status=status.HTTP_400_BAD_REQUEST)

        membership = CompanyMember.objects.filter(user=user_id, company=company_id).first()
        if not membership:
            return Response({"detail": "User is not a member of this company."}, status=status.HTTP_404_NOT_FOUND)

        membership.delete()

        return Response({"detail": "User has been successfully kicked from the company."}, status=status.HTTP_200_OK)



    @action(detail=False, methods=['get'], url_path='members')
    def list_members(self, request):
        company_id = request.query_params.get('company')

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            company = Company.objects.get(id=company_id)

            if company.visibility != Company.Visibility.VISIBLE:
                is_owner_or_member = CompanyMember.objects.filter(company=company, user=request.user).exists()
                if not is_owner_or_member and company.owner != request.user:
                    raise PermissionDenied()

            members = CompanyMember.objects.filter(company=company)
            serializer = CompanyMemberSerializer(members, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Company.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['get'], url_path='user-memberships')
    def user_memberships(self, request):
        user = request.user
        user_memberships = CompanyMember.objects.filter(user=user)
        companies = user_memberships.values('company', 'company__name')
        
        return Response(companies, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='is-member')
    def is_member_of_company(self, request):
        company_id = request.query_params.get('company')

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        is_member = CompanyMember.objects.filter(user=request.user, company=company_id).exists()

        return Response({"is_member": is_member}, status=status.HTTP_200_OK)    
    

    def list(self, request, *args, **kwargs):
        return Response(
            {"detail": "This endpoint is not available.  Use the members endpoint instead."},
            status=status.HTTP_403_FORBIDDEN
        )
        
    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Direct deletion is not allowed. Use the leave endpoint instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

