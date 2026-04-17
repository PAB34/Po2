from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserRead, UserUpdate
from app.services.cities import get_city_by_id


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email.lower())
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id)
    return db.scalar(statement)


def create_user(db: Session, payload: RegisterRequest) -> User:
    if get_user_by_email(db, payload.email):
        raise ValueError("EMAIL_ALREADY_EXISTS")
    if payload.city_id is not None and get_city_by_id(db, payload.city_id) is None:
        raise ValueError("CITY_NOT_FOUND")

    user = User(
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        nom=payload.nom.strip(),
        prenom=payload.prenom.strip(),
        telephone=payload.telephone.strip() if payload.telephone else None,
        city_id=payload.city_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def build_token_response(user: User) -> TokenResponse:
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token, token_type="bearer", user=UserRead.model_validate(user))


def update_user_profile(db: Session, user: User, payload: UserUpdate) -> User:
    user.nom = payload.nom.strip()
    user.prenom = payload.prenom.strip()
    user.telephone = payload.telephone.strip() if payload.telephone else None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("INVALID_PASSWORD")

    user.password_hash = get_password_hash(new_password)
    db.add(user)
    db.commit()
