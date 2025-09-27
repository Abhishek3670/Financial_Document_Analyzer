"""
Database models for the Financial Document Analyzer
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import uuid

Base = declarative_base()

class User(Base):
    """Enhanced User model for authentication and session tracking"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Authentication fields
    email = Column(String, unique=True, nullable=True, index=True)  # Nullable for backward compatibility
    username = Column(String, unique=True, nullable=True, index=True)  # Nullable for backward compatibility
    password_hash = Column(String, nullable=True)  # Nullable for backward compatibility
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Original session-based fields (keeping for backward compatibility)
    session_id = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now(), onupdate=func.now())
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Additional user profile fields
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Security and tracking
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime, nullable=True)
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def full_name(self):
        """Return full name if available"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return self.username
        else:
            return f"User {self.id[:8]}"
    
    @property
    def is_authenticated_user(self):
        """Check if this is a properly authenticated user (not just a session)"""
        return self.email is not None and self.password_hash is not None

class Document(Base):
    """Document metadata model"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)  # Optional: for persistent storage
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String, nullable=False, default="PDF")
    mime_type = Column(String, nullable=False, default="application/pdf")
    
    # File metadata
    upload_timestamp = Column(DateTime, default=func.now())
    file_hash = Column(String, nullable=True)  # For duplicate detection
    is_processed = Column(Boolean, default=False)
    is_stored_permanently = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    analyses = relationship("Analysis", back_populates="document", cascade="all, delete-orphan")

class Analysis(Base):
    """Analysis results model"""
    __tablename__ = "analyses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    
    # Analysis request info
    query = Column(Text, nullable=False)
    analysis_type = Column(String, nullable=False, default="comprehensive")
    
    # Analysis results
    result = Column(Text, nullable=False)  # Main analysis result
    summary = Column(Text, nullable=True)  # Optional summary
    
    # Analysis metadata
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Analysis metrics/confidence
    confidence_score = Column(Float, nullable=True)
    key_insights_count = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    document = relationship("Document", back_populates="analyses")

class AnalysisHistory(Base):
    """Historical tracking and audit log"""
    __tablename__ = "analysis_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)
    action = Column(String, nullable=False)  # created, updated, deleted, viewed
    timestamp = Column(DateTime, default=func.now())
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    details = Column(Text, nullable=True)  # JSON string with additional details
    ip_address = Column(String, nullable=True)
    
    # Relationships
    analysis = relationship("Analysis")
    user = relationship("User")

# Pydantic models for API responses
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional

# Authentication models
class UserRegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_activity: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

# Existing models (keeping for backward compatibility)
class DocumentResponse(BaseModel):
    id: str
    user_id: str
    original_filename: str
    file_size: int
    file_type: str
    upload_timestamp: datetime
    is_processed: bool
    is_stored_permanently: bool
    
    class Config:
        from_attributes = True

class AnalysisResponse(BaseModel):
    id: str
    user_id: str
    document_id: str
    query: str
    analysis_type: str
    result: str
    summary: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    status: str
    confidence_score: Optional[float] = None
    key_insights_count: Optional[int] = None
    
    # Include document info in response
    document: Optional[DocumentResponse] = None
    
    class Config:
        from_attributes = True

class AnalysisHistoryResponse(BaseModel):
    analyses: List[AnalysisResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool
    
    class Config:
        from_attributes = True

class CreateAnalysisRequest(BaseModel):
    query: str
    analysis_type: str = "comprehensive"

class AnalysisStatusResponse(BaseModel):
    status: str
    message: str
    analysis_id: Optional[str] = None
    progress_percentage: Optional[int] = None
