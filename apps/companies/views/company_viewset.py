from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Company, CompanyMember
from ..permission import IsOwner
from ..serializers import CompanyListSerializer, CompanyNamesSerializer, CompanySerializer


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
    
    @action(detail=False, methods=['get'], url_path='my-companies')
    def owner_companies(self, request):
        user = request.user
        companies = Company.objects.filter(owner=user)
        serializer = CompanyNamesSerializer(companies, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='user-companies')
    def user_companies(self, request):
        current_user = request.user
        user = request.query_params.get('user')
        
        if not user:
            return Response({"error": "User parameter is required"}, status=400)
        
        user_memberships = CompanyMember.objects.filter(user=user)
        company_ids = user_memberships.values_list('company', flat=True)
        companies = None
        
        companies = Company.objects.filter(
            Q(owner=user) | 
            Q(id__in=company_ids)
        )
        
        if current_user.id != user:
            companies = companies.exclude(visibility=Company.Visibility.HIDDEN)
            
        serializer = CompanyNamesSerializer(companies, many=True)
        return Response(serializer.data) 
