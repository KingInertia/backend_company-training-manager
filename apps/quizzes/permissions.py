from rest_framework import permissions

from apps.companies.models import CompanyMember


class IsCompanyAdminOrOwner(permissions.BasePermission):

    def has_permission(self, request, view):
        company_id = request.query_params.get('company_id')

        if not company_id:
            return False

        try:
            role = CompanyMember.objects.get(user=request.user, company_id=company_id).role
            if role not in [CompanyMember.Role.OWNER, CompanyMember.Role.ADMIN]:
                return False
        except CompanyMember.DoesNotExist:
            return False

        return True
