from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        # Apply globally: allow all authenticated users
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow GET, HEAD, OPTIONS to anyone authenticated
        if request.method in SAFE_METHODS:
            return True
        # Only allow modification if user is the owner
        return obj.created_by == request.user