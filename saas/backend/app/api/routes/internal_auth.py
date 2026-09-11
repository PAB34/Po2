from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.roles import is_external_role
from app.services.auth import authenticate_user

router = APIRouter(prefix="/internal", tags=["internal"])
security = HTTPBasic(auto_error=False)


@router.get("/basic-auth", include_in_schema=False)
def verify_basic_auth(
    credentials: HTTPBasicCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Response:
    """Garde du site principal : comptes Po2 uniquement (pas les comptes de l'outil thermique)."""
    user = None
    if credentials is not None:
        user = authenticate_user(db, credentials.username, credentials.password)
    if user is None or is_external_role(user.role):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": 'Basic realm="PatrimoineOp prive"'},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
