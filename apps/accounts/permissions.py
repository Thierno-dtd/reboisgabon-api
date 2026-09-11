from rest_framework.permissions import BasePermission
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .rbac import role_has_permission, VIEW, CREATE, EDIT, DELETE


class IsAdminRole(BasePermission):
    """Seuls les utilisateurs avec role=ADMIN passent."""

    message = "Seul un administrateur peut effectuer cette action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_admin
        )

from rest_framework.permissions import BasePermission, SAFE_METHODS
from .rbac import role_has_permission, VIEW, CREATE, EDIT, DELETE


class RBACPermission(BasePermission):
    """
    À utiliser sur les ModelViewSet. Définir `rbac_resource = '<clé_matrice>'`
    comme attribut de classe sur le ViewSet.
    """
    ACTION_TO_PERMISSION = {
        'list': VIEW, 'retrieve': VIEW,
        'create': CREATE,
        'update': EDIT, 'partial_update': EDIT,
        'destroy': DELETE,
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        resource = getattr(view, 'rbac_resource', None)
        permission_requise = self.ACTION_TO_PERMISSION.get(view.action)

        if resource is None or permission_requise is None:
            return True 

        return role_has_permission(request.user.role, resource, permission_requise)


class RBACAPIViewPermission(BasePermission):
    """
    À utiliser sur les APIView simples (dashboard, intelligence...).
    Sous-classer et définir `resource` et éventuellement `permission_requise`
    (par défaut VIEW).
    """
    resource = None
    permission_requise = VIEW

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return role_has_permission(request.user.role, self.resource, self.permission_requise)


class IsOwnerForAgentOrElevated(BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or user.role in ('ADMIN', 'SUPERVISEUR'):
            return True
        if user.role == 'FINANCIER':
            return request.method in SAFE_METHODS

        responsable = getattr(obj, 'responsable', None)
        if responsable is None and hasattr(obj, 'campagne'):
            responsable = obj.campagne.responsable
        if responsable is None and hasattr(obj, 'suivi'):
            responsable = obj.suivi.campagne.responsable

        if request.method in SAFE_METHODS:
            return True 
        return responsable == user