from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    external_sub: str | None = None


class UserProvisionRequest(BaseModel):
    external_sub: str
    username: str
    email: EmailStr
