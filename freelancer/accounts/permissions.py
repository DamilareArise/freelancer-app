from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow users with an admin role.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
                return True
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_admin
        )

class IsAdminOrOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a listing or admins to edit/delete it.
    """
    def has_object_permission(self, request, view, obj):
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

         # Allow if the user is an admin
        if request.user.is_admin and request.user.document_status == 'verified':
            return True

        # Allow if the user is the owner and their document is verified
        return obj.created_by == request.user and request.user.document_status == 'verified'