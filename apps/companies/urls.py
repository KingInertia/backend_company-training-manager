from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'companies', views.CompanyViewSet, basename='company')

urlpatterns = router.urls