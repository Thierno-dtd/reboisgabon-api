from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Seuls les utilisateurs avec role=ADMIN passent."""

    message = "Seul un administrateur peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_admin
        )