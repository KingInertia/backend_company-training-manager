from rest_framework.routers import DefaultRouter

from .views import company_member_viewset, company_viewset, invitation_viewset, request_viewset

router = DefaultRouter()
router.register(r'companies', company_viewset.CompanyViewSet, basename='company')
router.register(r'invitations', invitation_viewset.CompanyInvitationViewSet, basename='company-invitation')
router.register(r'requests', request_viewset.CompanyRequestViewSet, basename='company-request')
router.register(r'company-members', company_member_viewset.CompanyMemberViewSet, basename='company-member')

urlpatterns = router.urls
