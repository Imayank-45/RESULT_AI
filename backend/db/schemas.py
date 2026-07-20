from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    profile_image: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    profile_image: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class LoginHistoryResponse(BaseModel):
    id: int
    login_time: datetime
    logout_time: Optional[datetime] = None
    ip_address: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None

    class Config:
        from_attributes = True

class FullUserMeResponse(BaseModel):
    user: UserResponse
    recent_login_history: List[LoginHistoryResponse] = []
