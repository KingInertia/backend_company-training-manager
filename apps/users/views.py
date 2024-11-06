from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from .models import User
from .serializers import *
from typing import Type

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    pagination_class = PageNumberPagination
    
    def get_serializer_class(self):       
        if self.action == 'list':
            return UserListSerializer
        return UserSerializer    
        