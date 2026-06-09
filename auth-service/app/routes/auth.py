import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..jwks import get_claims_from_assertion
from ..models import User
from ..schemas import UserProvisionRequest, UserResponse

_PROVISION_SECRET = os.environ.get("INTERNAL_PROVISION_SECRET", "")

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def me(
    x_jwt_assertion: str = Header(..., alias="X-JWT-Assertion"),
    db: AsyncSession = Depends(get_db),
):
    try:
        claims = await get_claims_from_assertion(x_jwt_assertion)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    result = await db.execute(
        select(User).where(User.external_sub == claims.get("sub"))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user


@router.post("/users/provision", response_model=UserResponse, status_code=201)
async def provision_user(
    payload: UserProvisionRequest,
    x_internal_secret: str = Header(..., alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
):
    if not _PROVISION_SECRET or x_internal_secret != _PROVISION_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Idempotent — return existing record if already provisioned
    result = await db.execute(
        select(User).where(User.external_sub == payload.external_sub)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Link to an existing local account by email if one exists
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user:
        user.external_sub = payload.external_sub
    else:
        user = User(
            username=payload.username,
            email=payload.email,
            hashed_password=None,
            external_sub=payload.external_sub,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user
