from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .enums import RequestState, Role
from .models import Company, CompanyInvitation, CompanyMember, CompanyRequest
from .permission import IsInvitationReceiver, IsMemberOfCompany, IsOwner, IsOwnerOfCompany, IsRequestSender
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
            role=Role.OWNER.value  
        )
        
    def get_queryset(self):
        user = self.request.user
        user_memberships = CompanyMember.objects.filter(user=user)
        company_ids = user_memberships.values_list('company', flat=True)
        companies = (
        Company.objects.filter(owner=user) |
        Company.objects.filter(visibility='visible') |
        Company.objects.filter(id__in=company_ids)
        )

        return companies    


class CompanyInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CompanyInvitation.objects.filter(sender=user) | CompanyInvitation.objects.filter(receiver=user)

    def get_permissions(self):
        if self.action in ['create', 'cancelled_invitation']:
            return [IsOwnerOfCompany()]
        elif self.action in ['accept_invitation', 'decline_invitation']:
            return [IsInvitationReceiver()]
        return super().get_permissions()

    @action(detail=True, methods=['patch'], url_path='accept')
    def accept_invitation(self, request, *args, **kwargs):
        invitation = self.get_object()

        if invitation.status != RequestState.AWAITING_RESPONSE.value:
            return Response({"detail": "Invitation already processed."}, status=status.HTTP_400_BAD_REQUEST)

        invitation.status = RequestState.ACCEPTED.value
        invitation.save()

        CompanyMember.objects.create(
            user=request.user,
            company=invitation.company,
            role=Role.MEMBER.value
        )

        return Response(CompanyInvitationSerializer(invitation).data)

    @action(detail=True, methods=['patch'], url_path='decline')
    def decline_invitation(self, request, *args, **kwargs):
        invitation = self.get_object()

        if invitation.status != RequestState.AWAITING_RESPONSE.value:
            return Response({"detail": "Invitation already processed."}, status=status.HTTP_400_BAD_REQUEST)

        invitation.status = RequestState.DECLINED.value
        invitation.save()

        return Response(CompanyInvitationSerializer(invitation).data)

    @action(detail=True, methods=['patch'], url_path='cancelled')
    def cancelled_invitation(self, request, *args, **kwargs):
        invitation = self.get_object()
        
        if invitation.status != RequestState.AWAITING_RESPONSE.value:
            return Response({"detail": "Invitation already processed."}, status=status.HTTP_400_BAD_REQUEST)

        invitation.status = RequestState.CANCELLED.value
        invitation.save()

        return Response(CompanyInvitationSerializer(invitation).data)

    @action(detail=False, methods=['get'], url_path='owner-invitations')
    def list_owner_invitations(self, request, *args, **kwargs):
        owner = request.user
        invitations = CompanyInvitation.objects.filter(sender=owner)
        return Response(CompanyInvitationSerializer(invitations, many=True).data)

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
        return CompanyRequest.objects.filter(sender=user) | CompanyRequest.objects.filter(receiver=user)

    def get_permissions(self):
        if self.action in ['accept_request', 'decline_request']:
            return [IsOwnerOfCompany()]
        elif self.action in ['cancelled_request']:
            return [IsRequestSender ()]
        return super().get_permissions()

    @action(detail=True, methods=['patch'], url_path='accept')
    def accept_request(self, request, *args, **kwargs):
        request_obj = self.get_object()

        if request_obj.status != RequestState.AWAITING_RESPONSE.value:
            return Response({"detail": "Request already processed."}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.status = RequestState.ACCEPTED.value
        request_obj.save()

        CompanyMember.objects.create(
            user=request_obj.sender,
            company=request_obj.company,
            role=Role.MEMBER.value
        )

        return Response(CompanyRequestSerializer(request_obj).data)

    @action(detail=True, methods=['patch'], url_path='decline')
    def decline_request(self, request, *args, **kwargs):
        request_obj = self.get_object()

        if request_obj.status != RequestState.AWAITING_RESPONSE.value:
            return Response({"detail": "Request already processed."}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.status = RequestState.DECLINED.value
        request_obj.save()

        return Response(CompanyRequestSerializer(request_obj).data)

    @action(detail=True, methods=['patch'], url_path='cancelled')
    def cancelled_request(self, request, *args, **kwargs):
        request_obj = self.get_object()

        if request_obj.status != RequestState.AWAITING_RESPONSE.value:
            return Response({"detail": "Request already processed."}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.status = RequestState.CANCELLED.value
        request_obj.save()

        return Response(CompanyRequestSerializer(request_obj).data)

    @action(detail=False, methods=['get'], url_path='owner-requests')
    def list_owner_requests(self, request, *args, **kwargs):
        owner = request.user
        requests = CompanyRequest.objects.filter(receiver=owner)
        return Response(CompanyRequestSerializer(requests, many=True).data)

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

            if company.visibility != 'visible':
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

