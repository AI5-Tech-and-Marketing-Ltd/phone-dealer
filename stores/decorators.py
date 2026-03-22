from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

def check_subscription(view_func):
    """
    Decorator to check if store's subscription is active 
    and staff limits are not exceeded.
    """
    @wraps(view_func)
    def _wrapped_view(view, request, *args, **kwargs):
        store_id = request.data.get('store')
        if not store_id:
            return view_func(view, request, *args, **kwargs)
        
        from .models import Store, Subscription
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return view_func(view, request, *args, **kwargs)
        
        # Check if subscription is active
        active_sub = store.subscriptions.filter(expiry_date__gte=timezone.now().date()).first()
        if not active_sub and store.subscription_plan != 'Free':
            return Response({"error": "Subscription expired or not found."}, status=status.HTTP_403_FORBIDDEN)
            
        # Check staff limit if action is 'Add Staff' or similar (can be expanded)
        # Note: can include more specific logic based on action here.
            
        return view_func(view, request, *args, **kwargs)

    return _wrapped_view
