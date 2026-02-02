from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsArtistOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if hasattr(obj, "owner_id"):
            return obj.owner_id == request.user.id
        if hasattr(obj, "artist_id"):
            return obj.artist and obj.artist.owner_id == request.user.id
        return False
