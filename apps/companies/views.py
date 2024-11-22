from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from .models import Company
from .permission import IsOwner
from .serializers import CompanyListSerializer, CompanySerializer


class CompanyViewSet(viewsets.ModelViewSet):
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated, IsOwner] 
    
    def get_serializer_class(self):       
        if self.action == 'list':
            return CompanyListSerializer
        return CompanySerializer    
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)    
        
    def get_queryset(self):
        user = self.request.user
        return Company.objects.filter(owner=user) | Company.objects.filter(visibility='visible')
    