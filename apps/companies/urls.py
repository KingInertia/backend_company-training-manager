from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'companies', views.CompanyViewSet, basename='company')
router.register(r'invitations', views.CompanyInvitationViewSet, basename='company-invitation')
router.register(r'requests', views.CompanyRequestViewSet, basename='company-request')
router.register(r'company-members', views.CompanyMemberViewSet, basename='company-member')

urlpatterns = router.urls
