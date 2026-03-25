from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth & Profile
    path('api/auth/', include('accounts.urls_auth')),
    path('api/profile/', include('accounts.urls_profile')),
    
    # Store Management
    path('api/store/', include('stores.urls')),
    
    # Inventory
    path('api/inventory/', include('inventory.urls')),
    
    # Marketplace
    path('api/marketplace/', include('marketplace.urls')),
    
    # Billing
    path('api/billing/', include('billing.urls')),
    
    # SuperAdmin
    path('api/admin-portal/', include('admin_portal.urls')),

    # Schema & Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
