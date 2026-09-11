"""Rôles applicatifs transverses.

Un compte « externe » (bureau d'études) partage la table `users` et le mot de passe Po2,
mais n'a accès qu'à l'outil de métré thermique (thermique.patrimoineaucarre.com) :
jamais aux données de la Ville.
"""

THERMIQUE_EXTERNAL_ROLE = "THERMIQUE_EXTERNE"
EXTERNAL_ROLES = frozenset({THERMIQUE_EXTERNAL_ROLE})
ADMIN_ROLES = frozenset({"ADMIN", "SUPERADMIN"})


def normalize_role(role: str | None) -> str:
    return (role or "").strip().upper()


def is_external_role(role: str | None) -> bool:
    return normalize_role(role) in EXTERNAL_ROLES


def is_admin_role(role: str | None) -> bool:
    return normalize_role(role) in ADMIN_ROLES
