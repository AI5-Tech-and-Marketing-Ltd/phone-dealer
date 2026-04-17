from rest_framework import permissions
from django.utils import timezone

class HasActiveSubscription(permissions.BasePermission):
    """
    Permission class to check if a store owner has an active subscription.
    """
    message = "An active subscription is required to perform this action or view this data."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        
        if user.role == 'SuperUser':
            return True
        
        # Determine the store
        store = None
        if user.role == 'StoreOwner':
            store = user.stores.first()
        elif user.role == 'StoreKeeper':
            store = user.store
            
        if not store:
            return False
            
        try:
            subscription = store.subscription
            return subscription.is_active
        except Exception:
            return False
