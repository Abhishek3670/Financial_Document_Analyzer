"""
Authentication service for the Financial Document Analyzer
"""
import os
import secrets
import hashlib
import hmac
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import bcrypt
import logging

from models import User
from models import (
    UserRegisterRequest, UserLoginRequest, UserResponse, 
    TokenResponse, PasswordChangeRequest, PasswordResetRequest
)

logger = logging.getLogger(__name__)

class AuthService:
    """Authentication service for user management"""
    
    def __init__(self):
        # JWT Configuration
        self.secret_key = os.getenv('SECRET_KEY', self._generate_secret_key())
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
        self.refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7))
        
        # Security settings
        self.max_failed_attempts = int(os.getenv('MAX_FAILED_ATTEMPTS', 5))
        self.account_lockout_duration = int(os.getenv('ACCOUNT_LOCKOUT_DURATION', 300))  # 5 minutes
        
    def _generate_secret_key(self) -> str:
        """Generate a secret key for JWT signing"""
        return secrets.token_urlsafe(32)
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def create_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire.timestamp(), "iat": datetime.now(timezone.utc).timestamp()})
        
        # Simple JWT implementation using HMAC
        header = {"alg": self.algorithm, "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header, separators=(',', ':')).encode()
        ).decode().rstrip('=')
        
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(to_encode, default=str, separators=(',', ':')).encode()
        ).decode().rstrip('=')
        
        signature = hmac.new(
            self.secret_key.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT token"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).digest()
            expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')
            
            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                return None
            
            # Decode payload
            payload_padded = payload_b64 + '=' * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_padded))
            
            # Check expiration
            if datetime.now(timezone.utc).timestamp() > payload.get('exp', 0):
                return None
            
            return payload
            
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return None
    
    def register_user(self, session: Session, user_data: UserRegisterRequest) -> tuple[Optional[User], Optional[str]]:
        """Register a new user"""
        try:
            # Check if user already exists
            existing_user = session.query(User).filter(
                (User.email == user_data.email) | (User.username == user_data.username)
            ).first()
            
            if existing_user:
                if existing_user.email == user_data.email:
                    return None, "Email already registered"
                else:
                    return None, "Username already taken"
            
            # Create new user
            user = User(
                email=user_data.email,
                username=user_data.username,
                password_hash=self.hash_password(user_data.password),
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                is_active=True
            )
            
            session.add(user)
            session.flush()
            
            logger.info(f"User registered successfully: {user.email}")
            return user, None
            
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Database integrity error during registration: {e}")
            return None, "Registration failed due to database constraints"
        except Exception as e:
            session.rollback()
            logger.error(f"Registration error: {e}")
            return None, "Registration failed"
    
    def authenticate_user(self, session: Session, email: str, password: str) -> tuple[Optional[User], Optional[str]]:
        """Authenticate a user with email and password"""
        try:
            user = session.query(User).filter(User.email == email).first()
            
            if not user:
                return None, "Invalid email or password"
            
            if not user.is_active:
                return None, "Account is deactivated"
            
            # Check for account lockout
            if user.failed_login_attempts >= self.max_failed_attempts:
                if user.last_activity and (
                    datetime.now() - user.last_activity
                ).total_seconds() < self.account_lockout_duration:
                    return None, "Account is temporarily locked due to failed login attempts"
                else:
                    # Reset failed attempts after lockout period
                    user.failed_login_attempts = 0
            
            if not self.verify_password(password, user.password_hash):
                user.failed_login_attempts += 1
                session.commit()
                return None, "Invalid email or password"
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.last_login = datetime.now()
            session.commit()
            
            logger.info(f"User authenticated successfully: {user.email}")
            return user, None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None, "Authentication failed"
    
    def create_access_token(self, user: User) -> TokenResponse:
        """Create an access token for a user"""
        token_data = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
            "type": "access"
        }
        
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        access_token = self.create_token(token_data, expires_delta)
        
        # Create user response
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_activity=user.last_activity,
            last_login=user.last_login
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
            user=user_response
        )
    
    def get_current_user(self, session: Session, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        try:
            payload = self.decode_token(token)
            if not payload:
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            user = session.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                return None
            
            # Update last activity
            user.last_activity = datetime.now()
            session.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"Get current user error: {e}")
            return None
    
    def change_password(self, session: Session, user: User, request: PasswordChangeRequest) -> tuple[bool, Optional[str]]:
        """Change user password"""
        try:
            if not self.verify_password(request.current_password, user.password_hash):
                return False, "Current password is incorrect"
            
            if request.current_password == request.new_password:
                return False, "New password must be different from current password"
            
            user.password_hash = self.hash_password(request.new_password)
            session.commit()
            
            logger.info(f"Password changed for user: {user.email}")
            return True, None
            
        except Exception as e:
            logger.error(f"Password change error: {e}")
            return False, "Failed to change password"
    
    def generate_password_reset_token(self, session: Session, email: str) -> tuple[bool, Optional[str]]:
        """Generate a password reset token"""
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return False, "Email not found"
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            user.password_reset_token = reset_token
            user.password_reset_expires = datetime.now() + timedelta(hours=1)  # 1 hour expiry
            session.commit()
            
            logger.info(f"Password reset token generated for user: {user.email}")
            return True, reset_token
            
        except Exception as e:
            logger.error(f"Password reset token generation error: {e}")
            return False, "Failed to generate reset token"
    
    def reset_password(self, session: Session, token: str, new_password: str) -> tuple[bool, Optional[str]]:
        """Reset password using reset token"""
        try:
            user = session.query(User).filter(User.password_reset_token == token).first()
            if not user:
                return False, "Invalid reset token"
            
            if not user.password_reset_expires or datetime.now() > user.password_reset_expires:
                return False, "Reset token has expired"
            
            user.password_hash = self.hash_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            user.failed_login_attempts = 0  # Reset failed attempts
            session.commit()
            
            logger.info(f"Password reset completed for user: {user.email}")
            return True, None
            
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return False, "Failed to reset password"

# Global auth service instance
auth_service = AuthService()
