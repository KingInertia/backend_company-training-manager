from django.db.models import Subquery
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.quizzes.models import QuizResult

from ..models import Company, CompanyMember
from ..permission import IsMemberOfCompany, IsOwnerOfCompany
from ..serializers import CompanyMemberSerializer, MemberLastQuizSerializer


class CompanyMemberViewSet(viewsets.ModelViewSet):
    queryset = CompanyMember.objects.all()
    serializer_class = CompanyMemberSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        owner_actions = ['kick_from_company', 'appoint_admin', 'remove_admin']
        member_actions = ['leave_company']
        
        if self.action in member_actions:
            return [IsMemberOfCompany()]
        elif self.action in owner_actions:
            return [IsOwnerOfCompany()]
        return super().get_permissions()

    @action(detail=False, methods=['delete'], url_path='leave')
    def leave_company(self, request):
        company_id = request.data.get('company')
        
        company = get_object_or_404(Company, id=company_id)
                            
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
        
        company = get_object_or_404(Company, id=company_id)

        if company.owner.id == user_id:
            return Response({"detail": "You cannot kick the owner of the company."}, status=status.HTTP_403_FORBIDDEN)

        membership = CompanyMember.objects.filter(user=user_id, company=company_id).first()
        if not membership:
            return Response({"detail": "User is not a member of this company."}, status=status.HTTP_404_NOT_FOUND)

        membership.delete()

        return Response({"detail": "User has been successfully kicked from the company."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='appoint-admin')
    def appoint_admin(self, request):
        company_id = request.data.get('company')
        user_id = request.data.get('user')
        
        membership_exists = CompanyMember.objects.filter(user=user_id, company=company_id).exists()
        if not membership_exists:
            return Response({"detail": "User is not a member of this company."}, status=status.HTTP_404_NOT_FOUND)
        
        membership = CompanyMember.objects.filter(user=user_id, company=company_id).first()
        
        if membership.role in [CompanyMember.Role.ADMIN, CompanyMember.Role.OWNER]:
            return Response({"detail": "This user is already an admin or owner."}, status=status.HTTP_403_FORBIDDEN)
        
        membership.role = CompanyMember.Role.ADMIN
        membership.save()

        return Response({"detail": "User has been appointed as admin."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='remove-admin')
    def remove_admin(self, request):
        company_id = request.data.get('company')
        user_id = request.data.get('user')

        membership = get_object_or_404(CompanyMember, company=company_id, user=user_id)
        if not membership:
            return Response({"detail": "User is not a member of this company."}, status=status.HTTP_404_NOT_FOUND)

        if membership.role != CompanyMember.Role.ADMIN:
            return Response({"detail": "This user is not an admin."}, status=status.HTTP_400_BAD_REQUEST)

        membership.role = CompanyMember.Role.MEMBER
        membership.save()

        return Response({"detail": "Admin role has been removed from the user."}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='admins')
    def list_admins(self, request):
        company_id = request.query_params.get('company')

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            company = Company.objects.get(id=company_id)

            if company.visibility != Company.Visibility.VISIBLE:
                is_owner_or_member = CompanyMember.objects.filter(company=company, user=request.user).exists()
                if not is_owner_or_member and company.owner != request.user:
                    raise PermissionDenied()

            admins = CompanyMember.objects.filter(company_id=company_id, role=CompanyMember.Role.ADMIN)

            if not admins.exists():
                return Response([], status=status.HTTP_200_OK)

            serializer = CompanyMemberSerializer(admins, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Company.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='members')
    def list_members(self, request):
        company_id = request.query_params.get('company')
        user = request.user

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        visibility_and_role = CompanyMember.objects.filter(
            user=user, company_id=company_id
        ).select_related('company').values('company__visibility', 'role').first()

        if visibility_and_role is None:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        visibility = visibility_and_role.get('company__visibility')
        role = visibility_and_role.get('role')

        if visibility != Company.Visibility.VISIBLE and not role:
            raise PermissionDenied()

        if role == CompanyMember.Role.OWNER or role == CompanyMember.Role.ADMIN:
            quiz_results = QuizResult.objects.filter(
                quiz__company=company_id).order_by('user', '-created_at').distinct('user')

            members = CompanyMember.objects.filter(company=company_id).annotate(
                last_quiz=Subquery(quiz_results.values('created_at')[:1])
            )

            serializer = MemberLastQuizSerializer(members, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            members = CompanyMember.objects.filter(company=company_id)
            serializer = CompanyMemberSerializer(members, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='user-memberships')
    def user_memberships(self, request):
        user = request.user
        user_memberships = CompanyMember.objects.filter(user=user)
        companies = user_memberships.values('company', 'company__name')
        
        return Response(companies, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='member-role')
    def member_role(self, request):
        company_id = request.query_params.get('company')

        if not company_id:
            return Response({"detail": "Company ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        is_member = CompanyMember.objects.filter(user=request.user, company=company_id).exists()
        if not is_member:
            return Response({"role": None}, status=status.HTTP_200_OK)
        
        member_role = CompanyMember.objects.filter(
            user=request.user, company=company_id).values_list('role', flat=True).first()
        
        return Response({"role": member_role}, status=status.HTTP_200_OK)
    
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