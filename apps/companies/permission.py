from rest_framework import permissions

from .enums import Visibility
from .models import Company, CompanyMember


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.visibility == Visibility.VISIBLE or obj.owner == request.user
        
        return obj.owner == request.user
    
    
class IsOwnerOfCompany(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.data:
            try:
                invitation = view.get_object()
                return invitation.company.owner == request.user
            except Exception:
                return False

        company_id = request.data.get('company')
        if not company_id:
            return False
        
        try:
            company = Company.objects.get(id=company_id)
            return company.owner == request.user
        except Company.DoesNotExist:
            return False
    
    
class IsMemberOfCompany(permissions.BasePermission):
    def has_permission(self, request, view):
        company_id = request.data.get('company')
        
        try:
            return CompanyMember.objects.filter(
                user=request.user,
                company=company_id
            ).exists()
        except CompanyMember.DoesNotExist:
            return False