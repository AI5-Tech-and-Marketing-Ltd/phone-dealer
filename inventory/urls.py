from django.urls import path, include
from rest_framework import routers
from .views import ProductViewSet, AllocationViewSet
from .upload_views import CloudinarySignatureView, SetImageUrlView

router = routers.DefaultRouter()
router.register(r'allocations', AllocationViewSet, basename='allocation')
router.register(r'', ProductViewSet, basename='inventory')

urlpatterns = [
    path('upload/signature/', CloudinarySignatureView.as_view(), name='cloudinary-signature'),
    path('upload/set-url/', SetImageUrlView.as_view(), name='set-image-url'),
    path('', include(router.urls)),
]
