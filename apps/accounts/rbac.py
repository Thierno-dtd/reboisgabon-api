VIEW, CREATE, EDIT, DELETE = 'view', 'create', 'edit', 'delete'

RBAC_MATRIX = {
    'utilisateurs': {
        'ADMIN': {VIEW, CREATE, EDIT, DELETE},
    },
    'sites': {
        'ADMIN': {VIEW, CREATE, EDIT, DELETE},
        'SUPERVISEUR': {VIEW, CREATE, EDIT},
        'AGENT': {VIEW},
        'FINANCIER': {VIEW},
    },
    'campagnes': {
        'ADMIN': {VIEW, CREATE, EDIT, DELETE},
        'SUPERVISEUR': {VIEW, CREATE, EDIT},
        'AGENT': {VIEW, CREATE, EDIT},     
        'FINANCIER': {VIEW},
    },
    'suivis': {
        'ADMIN': {VIEW, CREATE, EDIT, DELETE},
        'SUPERVISEUR': {VIEW, CREATE, EDIT},
        'AGENT': {VIEW, CREATE, EDIT},     
        'FINANCIER': {VIEW},
    },
    'essences': {
        'ADMIN': {VIEW, CREATE, EDIT, DELETE},
        'SUPERVISEUR': {VIEW, CREATE, EDIT},
        'AGENT': {VIEW},
        'FINANCIER': {VIEW},
    },
    'objectifs': {
        'ADMIN': {VIEW, CREATE, EDIT, DELETE},
        'SUPERVISEUR': {VIEW, CREATE, EDIT},
        'AGENT': {VIEW},
        'FINANCIER': {VIEW},
    },
    'finances': {
        'ADMIN': {VIEW, CREATE, EDIT, DELETE},
        'FINANCIER': {VIEW, CREATE, EDIT, DELETE},
        'SUPERVISEUR': {VIEW},
        'AGENT': set(),
    },
    'audit': {
        'ADMIN': {VIEW},
    },
    'intelligence': {
        'ADMIN': {VIEW, CREATE},
        'SUPERVISEUR': {VIEW, CREATE},
        'AGENT': {VIEW},
        'FINANCIER': set(),
    },
}


def role_has_permission(role, resource, permission):
    if role is None:
        return False
    return permission in RBAC_MATRIX.get(resource, {}).get(role, set())