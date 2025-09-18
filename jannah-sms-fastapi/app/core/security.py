"""
Security utilities for authentication and authorization.
Designed to be simple but secure for elderly users.
"""

from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token authentication
security = HTTPBearer(auto_error=False)

# Simple admin credentials (in production, use proper user management)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "secret"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate hash for a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
        return {"username": username}
    except JWTError:
        return None


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current user from token, but don't raise error if not authenticated.
    Used for pages that work for both authenticated and unauthenticated users.
    """
    if credentials:
        user = verify_token(credentials.credentials)
        if user:
            return user
    
    # Check session cookie as fallback (elderly-friendly)
    session_token = request.cookies.get("session_token")
    if session_token:
        user = verify_token(session_token)
        if user:
            return user
    
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """Get current authenticated user or raise 401."""
    user = await get_current_user_optional(request, credentials)
    
    if not user:
        # For web interface, redirect to login instead of JSON error
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            # Redirect to login page for web interface
            return RedirectResponse(url="/login", status_code=302)
    
    return user


def authenticate_user(username: str, password: str) -> Union[dict, bool]:
    """
    Authenticate user with username and password.
    Returns user dict if successful, False otherwise.
    """
    # Simple admin authentication (expand this for multiple users)
    if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH):
        return {
            "username": username,
            "full_name": "Administrator",
            "email": "admin@jannah-sms.com",
            "is_admin": True
        }
    
    return False


# Dependency for admin-only endpoints
async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure current user is an admin."""
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# For elderly users: simple cookie-based session management
class SessionManager:
    """Simple session management for elderly-friendly web interface."""
    
    @staticmethod
    def create_session_cookie(username: str) -> str:
        """Create session token for cookie."""
        return create_access_token({"sub": username})
    
    @staticmethod
    def verify_session_cookie(token: str) -> Optional[dict]:
        """Verify session cookie token."""
        return verify_token(token)