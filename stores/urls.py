from django.urls import path, include
from rest_framework import routers
from .views import (
    StoreViewSet, StoreStaffViewSet, AddStaffView, ReduceStaffView, StoreStaffCreateView
)

router = routers.DefaultRouter()
router.register(r'staff', StoreStaffViewSet, basename='store-staff')
router.register(r'', StoreViewSet, basename='store')

urlpatterns = [
    path('subscriptions/add-staff/', AddStaffView.as_view(), name='add-staff-slot'),
    path('staff/account-create/', StoreStaffCreateView.as_view(), name='add-staff-account'),
    path('subscriptions/reduce-staff/', ReduceStaffView.as_view(), name='reduce-staff'),
    path('', include(router.urls)),
]
