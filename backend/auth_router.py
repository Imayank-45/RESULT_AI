from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import user_agents

from backend.db.database import get_db
from backend.db.models import User, LoginHistory
from backend.db.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    ProfileUpdateRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    FullUserMeResponse,
    LoginHistoryResponse
)
from backend.db.auth import (
    verify_password,
    get_password_hash,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    SECRET_KEY,
    REFRESH_SECRET_KEY,
    REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def parse_user_agent(request: Request):
    """Parse client IP address, Browser, and Operating System from request."""
    ip = request.client.host if request.client else "Unknown"
    # Support reverse proxy client IP headers
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()

    ua_string = request.headers.get("User-Agent", "")
    browser_str = "Unknown Browser"
    os_str = "Unknown OS"

    if ua_string:
        try:
            ua = user_agents.parse(ua_string)
            browser_str = f"{ua.browser.family} {ua.browser.version_string}".strip()
            os_str = f"{ua.os.family} {ua.os.version_string}".strip()
        except Exception:
            browser_str = ua_string[:50]

    return ip, browser_str, os_str


@auth_router.post("/login", response_model=TokenResponse)
def login(login_req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user, record login history, and return JWT tokens."""
    user = db.query(User).filter(User.email == login_req.email.lower().strip()).first()
    
    if not user or not verify_password(login_req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact administrator."
        )

    # Record login history
    ip, browser, os_name = parse_user_agent(request)
    login_history = LoginHistory(
        user_id=user.id,
        login_time=datetime.utcnow(),
        ip_address=ip,
        browser=browser,
        os=os_name
    )
    db.add(login_history)

    # Update user's last_login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Calculate token duration based on Remember Me
    access_delta = timedelta(days=REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS) if login_req.remember_me else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email}, expires_delta=access_delta)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@auth_router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Log out active session and record logout time in LoginHistory."""
    # Find latest open login record for current user
    latest_history = (
        db.query(LoginHistory)
        .filter(LoginHistory.user_id == current_user.id, LoginHistory.logout_time.is_(None))
        .order_by(LoginHistory.login_time.desc())
        .first()
    )
    if latest_history:
        latest_history.logout_time = datetime.utcnow()
        db.commit()

    return {"message": "Logged out successfully."}


@auth_router.post("/refresh")
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    payload = decode_token(req.refresh_token, REFRESH_SECRET_KEY)
    
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token type.")
        
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or inactive account.")

    new_access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@auth_router.get("/me", response_model=FullUserMeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return authenticated user profile and recent 10 login histories."""
    recent_history = (
        db.query(LoginHistory)
        .filter(LoginHistory.user_id == current_user.id)
        .order_by(LoginHistory.login_time.desc())
        .limit(10)
        .all()
    )
    
    return FullUserMeResponse(
        user=UserResponse.model_validate(current_user),
        recent_login_history=[LoginHistoryResponse.model_validate(h) for h in recent_history]
    )


@auth_router.put("/profile", response_model=UserResponse)
def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update name, phone, or profile picture for current user."""
    if profile_data.name is not None and profile_data.name.strip():
        current_user.name = profile_data.name.strip()
    if profile_data.phone is not None:
        current_user.phone = profile_data.phone.strip()
    if profile_data.profile_image is not None:
        current_user.profile_image = profile_data.profile_image

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@auth_router.put("/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password."""
    if not verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match."
        )

    validate_password_strength(req.new_password)

    current_user.password_hash = get_password_hash(req.new_password)
    db.commit()

    return {"message": "Password changed successfully."}


@auth_router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Forgot password request handler."""
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user:
        # Prevent user enumeration security risk
        return {"message": "If an account with that email exists, password reset instructions have been processed."}

    # For single-user setup, returns confirmation message
    return {"message": "If an account with that email exists, password reset instructions have been processed."}
