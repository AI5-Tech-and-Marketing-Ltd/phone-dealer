from django.urls import path, include
from rest_framework import routers
from .views import (
    ProductViewSet, AllocationViewSet, ConditionViewSet, 
    TacListView, TacCreateView, TacBulkCreateView,
    TacUploadView, TacSearchView
)

router = routers.DefaultRouter()
router.register(r'conditions', ConditionViewSet, basename='condition')
router.register(r'allocations', AllocationViewSet, basename='allocation')
router.register(r'', ProductViewSet, basename='inventory')

urlpatterns = [
    # --- TAC Management (SuperUser) ---
    path('tac/',         TacListView.as_view(),       name='tac-list'),
    path('tac/create/',  TacCreateView.as_view(),     name='tac-create'),
    path('tac/bulk/',    TacBulkCreateView.as_view(), name='tac-bulk'),
    path('tac/upload/',  TacUploadView.as_view(),     name='tac-upload'),
    path('tac/search/',  TacSearchView.as_view(),     name='tac-search'),

    # --- Legacy (keep for one cycle) ---
    path('tac-list/',    TacListView.as_view(),       name='tac-list-legacy'),

    path('', include(router.urls)),
]
