from rest_framework import permissions

class IsSuperUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'SuperUser'

class IsStoreOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'StoreOwner'

class IsStoreKeeper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'StoreKeeper'

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # If object is a store, check its owner. If it's something else with an 'owner' or 'store.owner' path.
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'store'):
            return obj.store.owner == request.user
        return False
