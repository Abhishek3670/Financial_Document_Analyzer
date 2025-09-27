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
    """User/Session model for tracking analysis sessions"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now(), onupdate=func.now())
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")

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
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class UserResponse(BaseModel):
    id: str
    session_id: str
    created_at: datetime
    last_activity: datetime
    
    class Config:
        from_attributes = True

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
