from rest_framework import permissions

from apps.companies.models import CompanyMember


class IsCompanyAdminOrOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        company_id = request.query_params.get('company_id')

        if not company_id:
            return False

        is_admin_or_owner = CompanyMember.objects.filter(
            user=request.user,
            company_id=company_id,
            role__in=[CompanyMember.Role.OWNER, CompanyMember.Role.ADMIN]
        ).exists()

        return is_admin_or_owner
