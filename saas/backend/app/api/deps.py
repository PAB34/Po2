from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.roles import is_external_role
from app.core.security import decode_token
from app.models.user import User
from app.services.auth import get_user_by_id

security = HTTPBearer(auto_error=False)


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Tout compte actif, interne ou externe : outil thermique, profil, mot de passe."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
        )

    try:
        payload = decode_token(credentials.credentials)
        subject = payload.get("sub")
        user_id = int(subject)
    except (JWTError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide.",
        ) from None

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé.",
        )

    return user


def get_current_user(user: User = Depends(get_authenticated_user)) -> User:
    """Compte Po2 : les comptes externes (bureaux d'études) sont limités à l'outil thermique."""
    if is_external_role(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte donne accès uniquement à l'outil de métré thermique.",
        )
    return user
