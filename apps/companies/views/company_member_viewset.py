from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Company, CompanyMember
from ..permission import IsMemberOfCompany, IsOwnerOfCompany
from ..serializers import CompanyMemberSerializer


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
        
        company = Company.objects.get(id=company_id)
                            
        if company.owner == request.user:
            return Response({"detail": "Owner cannot leave the company."}, status=status.HTTP_403_FORBIDDEN)       

        try:
            membership = CompanyMember.objects.get(user=request.user, company=company_id)
            membership.delete()
            return Response({"detail": "You have successfully left the company."}, status=status.HTTP_200_OK)
        except CompanyMember.DoesNotExist:
            raise Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['delete'], url_path='kick')
    def kick_from_company(self, request):
        company_id = request.data.get('company')
        user_id = request.data.get('user')  
        
        if not company_id or not user_id:
            return Response({"detail": "Company ID and User ID are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        company = Company.objects.get(id=company_id)

        if company.owner.id == user_id:
            return Response({"detail": "You cannot kick the owner of the company."}, status=status.HTTP_403_FORBIDDEN)

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