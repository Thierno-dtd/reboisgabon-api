from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, MyProfileView

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')

urlpatterns = router.urls

urlpatterns += [
    path('me/update/', MyProfileView.as_view({'patch': 'partial_update_me'}), name='me-update'),
    path('me/change-password/', MyProfileView.as_view({'post': 'change_password'}), name='me-change-password'),
]