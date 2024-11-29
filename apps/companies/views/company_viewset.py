from django.db.models import Q
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from ..models import Company, CompanyMember
from ..permission import IsOwner
from ..serializers import CompanyListSerializer, CompanySerializer


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
