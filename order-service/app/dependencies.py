from fastapi import Header, HTTPException, status

from .jwks import get_claims_from_assertion


async def get_current_user(
    x_jwt_assertion: str = Header(..., alias="X-JWT-Assertion"),
) -> dict:
    try:
        return await get_claims_from_assertion(x_jwt_assertion)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
