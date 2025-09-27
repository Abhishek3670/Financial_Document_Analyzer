"""
Authentication middleware and dependencies for FastAPI
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging

from database import get_db_session
from auth import auth_service
from models import User

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()

class AuthMiddleware:
    """Authentication middleware for FastAPI"""
    
    def __init__(self):
        self.auth_service = auth_service
    
    async def __call__(self, request: Request, call_next):
        """Process request through authentication middleware"""
        response = await call_next(request)
        return response

# Dependency functions
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_db_session)
) -> User:
    """
    FastAPI dependency to get current authenticated user
    Raises HTTPException if token is invalid or user not found
    """
    try:
        token = credentials.credentials
        user = auth_service.get_current_user(session, token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to get current active authenticated user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_current_verified_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    FastAPI dependency to get current verified authenticated user
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user

def get_optional_user(
    request: Request,
    session: Session = Depends(get_db_session)
) -> Optional[User]:
    """
    FastAPI dependency to get current user if authenticated, None otherwise
    This is useful for endpoints that work for both authenticated and anonymous users
    """
    try:
        # Try to get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.split(" ")[1]
        user = auth_service.get_current_user(session, token)
        return user
        
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None

def get_user_or_session(
    request: Request,
    session: Session = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_user)
) -> User:
    """
    FastAPI dependency for backward compatibility
    Returns authenticated user if available, otherwise creates/gets session user
    """
    if current_user and current_user.is_authenticated_user:
        return current_user
    
    # Fallback to session-based user creation (for backward compatibility)
    from services import UserService
    
    try:
        # Try to get session_id from headers or cookies
        session_id = request.headers.get("X-Session-ID") or request.cookies.get("session_id")
        
        if session_id:
            user = UserService.get_user_by_session_id(session, session_id)
            if user:
                return user
        
        # Create new session user
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        user = UserService.create_user(session, ip_address, user_agent)
        session.commit()
        
        return user
        
    except Exception as e:
        logger.error(f"Failed to get user or create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to establish user session"
        )

# Custom exceptions
class AuthenticationError(Exception):
    """Custom authentication error"""
    pass

class AuthorizationError(Exception):
    """Custom authorization error"""
    pass

# Utility functions
def require_auth(user: Optional[User]) -> User:
    """
    Utility function to require authentication
    Raises HTTPException if user is not authenticated
    """
    if not user or not user.is_authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_verification(user: User) -> User:
    """
    Utility function to require email verification
    Raises HTTPException if user is not verified
    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return user

def check_user_permissions(user: User, required_permissions: list = None) -> bool:
    """
    Check if user has required permissions
    This is a placeholder for future role-based access control
    """
    if not user.is_active:
        return False
    
    # Add your permission logic here
    # For now, all active users have all permissions
    return True

def require_permissions(user: User, permissions: list = None) -> User:
    """
    Utility function to require specific permissions
    """
    if not check_user_permissions(user, permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return user
