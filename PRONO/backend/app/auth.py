"""Routes d'auth + dépendance get_current_user (JWT Bearer)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel

from app.db import get_user_by_email, get_user_by_id, update_password_hash
from app.security import verify_password, get_password_hash, create_access_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise.")
    try:
        payload = decode_token(creds.credentials)
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide.") from None
    user = get_user_by_id(user_id)
    if user is None or not user["is_active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur non trouvé.")
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect.")
    token = create_access_token(str(user["id"]))
    return TokenResponse(access_token=token, email=user["email"])


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {"email": user["email"]}


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, user=Depends(get_current_user)):
    if not verify_password(payload.current_password, user["password_hash"]):
        # 400 et non 401 : le jeton (l'authentification) est valide, c'est la
        # donnée soumise (mot de passe actuel) qui est incorrecte. Un 401 ici
        # ferait croire au frontend que la session a expiré et le déconnecterait.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect.")
    if len(payload.new_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le nouveau mot de passe doit faire au moins 8 caractères.")
    update_password_hash(user["id"], get_password_hash(payload.new_password))
    return {"ok": True}
