# Authentication imports
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import uuid
import asyncio
import logging
from pathlib import Path
import magic
from datetime import datetime
from typing import List, Optional

from crewai import Crew, Process
from agents import financial_analyst, data_extractor, investment_analyst, risk_analyst
from task import comprehensive_financial_analysis

# Database imports
from database import init_database, get_db_session, get_database_manager
from services import UserService, DocumentService, AnalysisService, AnalysisHistoryService
from models import (
    User,
    AnalysisResponse, DocumentResponse, AnalysisHistoryResponse,
    CreateAnalysisRequest, AnalysisStatusResponse,
    # Authentication models
    UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    UserProfileUpdate
)

# Authentication imports
from auth import auth_service
from auth_middleware import (
    get_current_user, get_current_active_user, get_current_verified_user,
    get_optional_user, get_user_or_session
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database on startup
try:
    db_manager = init_database()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise

app = FastAPI(
    title="Financial Document Analyzer",
    description="AI-powered financial document analysis system with persistent storage",
    version="2.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.pdf'}
UPLOAD_DIR = "data"
KEEP_UPLOADED_FILES = os.getenv('KEEP_UPLOADED_FILES', 'false').lower() == 'true'

def get_client_info(request: Request) -> dict:
    """Extract client information from request"""
    return {
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent', None)
    }

def get_or_create_user(session: Session, request: Request) -> str:
    """Get or create user session"""
    # In a real application, you might use session cookies or JWT tokens
    # For now, we'll create a new user session for each request
    # You can extend this to handle session persistence
    client_info = get_client_info(request)
    user = UserService.create_user(
        session=session,
        ip_address=client_info['ip_address'],
        user_agent=client_info['user_agent']
    )
    session.commit()
    return user.id

def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file"""
    try:
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            return False, f"Invalid file type. Only PDF files are allowed. Got: {file_extension}"
        
        # Check if filename is safe
        if not file.filename or '..' in file.filename or '/' in file.filename:
            return False, "Invalid filename"
        
        return True, "Valid file"
        
    except Exception as e:
        logger.error(f"Error validating file: {e}")
        return False, f"File validation error: {str(e)}"

def run_crew(query: str, file_path: str) -> str:
    """Run the CrewAI crew for financial analysis"""
    try:
        financial_crew = Crew(
            agents=[financial_analyst, data_extractor, investment_analyst, risk_analyst],
            tasks=[comprehensive_financial_analysis],
            process=Process.sequential,
            verbose=True
        )

        result = financial_crew.kickoff({'query': query, 'file_path': file_path})
        
        # Log the raw result for debugging
        logger.info(f"CrewAI raw result type: {type(result)}")
        logger.info(f"CrewAI raw result length: {len(str(result)) if result else 0}")
        logger.info(f"CrewAI raw result preview (first 200 chars): {str(result)[:200] if result else 'None'}")
        
        # Ensure we have a proper string result
        if result is None:
            result = "No analysis result was generated. Please try again."
        elif hasattr(result, 'raw'):
            # If result has a raw attribute, use that
            result = str(result.raw)
        else:
            result = str(result)
            
        # Check if the result is too short or appears to be incomplete
        if len(result.strip()) < 50:
            logger.warning(f"CrewAI result appears incomplete: '{result}'")
            
            # Try to extract PDF content and provide a basic analysis
            try:
                from tools import financial_document_tool
                pdf_content = financial_document_tool._run(file_path)
                
                # Provide a fallback analysis
                fallback_analysis = generate_fallback_analysis(pdf_content[:2000], query)  # First 2000 chars
                logger.info("Generated fallback analysis due to CrewAI incomplete result")
                return fallback_analysis
                
            except Exception as fallback_error:
                logger.error(f"Fallback analysis also failed: {fallback_error}")
                return f"""# Analysis Result - Technical Issue

**Query:** {query}

**Status:** We encountered a technical issue while processing your financial document. 

**Issue Details:**
- The AI analysis system returned an incomplete result
- Fallback analysis generation also encountered an error
- This may be due to document complexity or temporary service issues

**Recommendation:**
1. Please try uploading the document again
2. Ensure the PDF is not corrupted and contains readable text
3. Try with a simpler analysis query if the issue persists

**Technical Details:**
- Original result length: {len(result.strip())} characters
- Original result: "{result.strip()}"
- File processed: {file_path}

We apologize for the inconvenience. Please contact support if this issue continues."""

        return result
        
    except Exception as e:
        logger.error(f"Error running crew: {e}")
        # Generate a fallback analysis in case of complete failure
        try:
            from tools import financial_document_tool
            pdf_content = financial_document_tool._run(file_path)
            fallback_analysis = generate_fallback_analysis(pdf_content[:2000], query)
            logger.info("Generated fallback analysis due to CrewAI exception")
            return fallback_analysis
        except Exception as fallback_error:
            logger.error(f"Fallback analysis failed: {fallback_error}")
            raise HTTPException(
                status_code=500, 
                detail=f"Analysis processing error: {str(e)}"
            )

def generate_fallback_analysis(pdf_content: str, query: str) -> str:
    """Generate a basic fallback analysis when CrewAI fails"""
    import re
    
    # Extract basic information
    content_lower = pdf_content.lower()
    
    # Try to identify company name
    company_name = "Unknown Company"
    for line in pdf_content.split('\n')[:10]:  # Check first 10 lines
        if len(line.strip()) > 3 and len(line.strip()) < 50:
            if any(word in line.lower() for word in ['inc', 'corp', 'company', 'ltd']):
                company_name = line.strip()
                break
    
    # Look for financial indicators
    revenue_mentions = len(re.findall(r'\$[\d,.]+ [mb]illion|\$[\d,.]+[mb]|\$[\d,]+', content_lower))
    has_revenue = 'revenue' in content_lower or 'sales' in content_lower
    has_profit = 'profit' in content_lower or 'income' in content_lower or 'earnings' in content_lower
    has_cash = 'cash' in content_lower
    has_debt = 'debt' in content_lower
    
    # Extract document type
    doc_type = "Financial Report"
    if 'quarterly' in content_lower or 'q1' in content_lower or 'q2' in content_lower or 'q3' in content_lower or 'q4' in content_lower:
        doc_type = "Quarterly Report"
    elif 'annual' in content_lower:
        doc_type = "Annual Report"
    elif '10-k' in content_lower:
        doc_type = "Annual Report (10-K)"
    elif '10-q' in content_lower:
        doc_type = "Quarterly Report (10-Q)"
    
    # Generate the analysis
    analysis = f"""# Financial Document Analysis - Basic Report

**⚠️ Note:** This is a basic analysis generated due to technical limitations with our AI system. For detailed insights, please try analyzing the document again.

## Document Overview
- **Company:** {company_name}
- **Document Type:** {doc_type}
- **Analysis Query:** {query}

## Content Summary
- **Document Length:** {len(pdf_content):,} characters
- **Financial Data Present:** {'Yes' if revenue_mentions > 0 else 'Limited'}
- **Key Sections Detected:**
  - Revenue/Sales Information: {'✓' if has_revenue else '✗'}
  - Profit/Earnings Data: {'✓' if has_profit else '✗'}
  - Cash Flow Information: {'✓' if has_cash else '✗'}
  - Debt Information: {'✓' if has_debt else '✗'}

## Basic Analysis
Based on the document content:

1. **Document Quality:** The PDF was successfully processed and contains {len(pdf_content):,} characters of text.

2. **Financial Content:** {"Multiple financial figures and metrics were found in the document." if revenue_mentions > 2 else "Some financial information appears to be present." if revenue_mentions > 0 else "Limited financial metrics detected in the initial scan."}

3. **Recommendation:** For a comprehensive analysis of this {doc_type.lower()}, please:
   - Try re-uploading the document
   - Ensure your query is specific (e.g., "Focus on revenue growth" or "Analyze profitability metrics")
   - Contact support if technical issues persist

## Document Preview (First 500 characters)
```
{pdf_content[:500]}...
```

---
*This basic analysis was generated automatically when our advanced AI system encountered technical difficulties. Please try again for detailed insights.*"""

    return analysis


@app.get("/")
async def root():
    """Health check endpoint"""
    db_info = get_database_manager().get_database_info()
    return {
        "message": "Financial Document Analyzer API is running",
        "status": "healthy",
        "version": "2.0.0",
        "features": ["persistent_storage", "analysis_history", "user_sessions"],
        "database": db_info
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    db_healthy = get_database_manager().health_check()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "services": {
            "api": "running",
            "database": "healthy" if db_healthy else "unhealthy",
            "file_upload": "available",
            "ai_analysis": "available"
        },
        "database_info": get_database_manager().get_database_info()
    }


# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@app.post("/auth/register", response_model=TokenResponse)
async def register_user(
    user_data: UserRegisterRequest,
    session: Session = Depends(get_db_session)
):
    """Register a new user"""
    try:
        user, error = auth_service.register_user(session, user_data)
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        session.commit()
        
        # Create access token for the new user
        token_response = auth_service.create_access_token(user)
        
        logger.info(f"User registered successfully: {user.email}")
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.post("/auth/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLoginRequest,
    session: Session = Depends(get_db_session)
):
    """Authenticate user and return access token"""
    try:
        user, error = auth_service.authenticate_user(
            session, login_data.email, login_data.password
        )
        
        if error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error
            )
        
        # Create access token
        token_response = auth_service.create_access_token(user)
        
        logger.info(f"User logged in successfully: {user.email}")
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.post("/auth/logout")
async def logout_user(current_user: UserResponse = Depends(get_current_user)):
    """Logout user (client should discard token)"""
    try:
        logger.info(f"User logged out: {current_user.email}")
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"message": "Logged out"}

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_profile(current_user: UserResponse = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@app.put("/auth/profile", response_model=UserResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user),
    session: Session = Depends(get_db_session)
):
    """Update user profile"""
    try:
        # Get the actual user object from database
        user = session.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update profile fields
        if profile_update.first_name is not None:
            user.first_name = profile_update.first_name
        if profile_update.last_name is not None:
            user.last_name = profile_update.last_name
        if profile_update.email is not None:
            # Check if email is already taken
            existing_user = session.query(User).filter(
                User.email == profile_update.email,
                User.id != user.id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already taken"
                )
            user.email = profile_update.email
            user.is_verified = False  # Require re-verification
        
        session.commit()
        
        # Return updated user response
        updated_user = UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_activity=user.last_activity,
            last_login=user.last_login
        )
        
        logger.info(f"Profile updated for user: {user.email}")
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@app.post("/auth/change-password")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: UserResponse = Depends(get_current_user),
    session: Session = Depends(get_db_session)
):
    """Change user password"""
    try:
        # Get the actual user object from database
        user = session.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        success, error = auth_service.change_password(session, user, password_change)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        logger.info(f"Password changed for user: {user.email}")
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@app.post("/auth/forgot-password")
async def forgot_password(
    reset_request: PasswordResetRequest,
    session: Session = Depends(get_db_session)
):
    """Request password reset"""
    try:
        success, token = auth_service.generate_password_reset_token(
            session, reset_request.email
        )
        
        if not success:
            # Return success even if email not found for security
            return {"message": "If the email exists, a reset link has been sent"}
        
        # In a real application, you would send an email here
        # For now, we'll log the token (in production, this should be sent via email)
        logger.info(f"Password reset token generated: {token}")
        
        return {
            "message": "If the email exists, a reset link has been sent",
            "token": token  # Remove this in production!
        }
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        return {"message": "If the email exists, a reset link has been sent"}

@app.post("/auth/reset-password")
async def reset_password(
    reset_confirm: PasswordResetConfirm,
    session: Session = Depends(get_db_session)
):
    """Reset password using token"""
    try:
        success, error = auth_service.reset_password(
            session, reset_confirm.token, reset_confirm.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reset password"
        )

# =============================================================================
# END AUTHENTICATION ROUTES
# =============================================================================
@app.post("/analyze", response_model=dict)
async def analyze_document_endpoint(
    request: Request,
    file: UploadFile = File(..., description="PDF file to analyze (max 50MB)"),
    query: str = Form(
        default="Provide a comprehensive financial analysis of this document", 
        description="Specific analysis query or instructions"
    ),
    keep_file: bool = Form(default=False, description="Keep file after processing"),
    session: Session = Depends(get_db_session)
):
    """Analyze financial document and provide comprehensive investment recommendations"""
    
    analysis_id = None
    document_id = None
    file_path = None
    user_id = None
    
    try:
        # Get or create user session
        user_id = get_or_create_user(session, request)
        logger.info(f"Processing request for user: {user_id}")
        
        # Validate file
        is_valid, validation_msg = validate_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=validation_msg)
        
        # Read file content and check size
        content = await file.read()
        file_size = len(content)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Max size: {MAX_FILE_SIZE//1024//1024}MB, got: {file_size//1024//1024}MB"
            )
        
        # Validate file type using python-magic (more reliable than extension)
        try:
            file_mime = magic.from_buffer(content, mime=True)
            if file_mime != 'application/pdf':
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid file format. Expected PDF, got: {file_mime}"
                )
        except:
            # Fallback if python-magic is not available
            logger.warning("python-magic not available, using extension-based validation")
        
        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        stored_filename = f"financial_document_{file_id}.pdf"
        file_path = os.path.join(UPLOAD_DIR, stored_filename)
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File saved: {file_path}, size: {file_size} bytes")
        
        # Create document record in database
        document = DocumentService.create_document(
            session=session,
            user_id=user_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=file_path if (keep_file or KEEP_UPLOADED_FILES) else None,
            file_size=file_size,
            file_type="PDF",
            mime_type=file_mime if 'file_mime' in locals() else "application/pdf",
            file_content=content
        )
        document_id = document.id
        session.commit()
        
        # Validate and sanitize query
        if not query or not query.strip():
            query = "Provide a comprehensive financial analysis of this document"
        
        # Limit query length to prevent abuse
        query = query.strip()[:1000]  # Max 1000 characters
        
        # Create analysis record
        analysis = AnalysisService.create_analysis(
            session=session,
            user_id=user_id,
            document_id=document_id,
            query=query,
            analysis_type="comprehensive"
        )
        analysis_id = analysis.id
        session.commit()
        
        # Log analysis creation
        AnalysisHistoryService.log_action(
            session=session,
            analysis_id=analysis_id,
            action="created",
            user_id=user_id,
            details=f"Analysis started for file: {file.filename}",
            ip_address=get_client_info(request)['ip_address']
        )
        session.commit()
        
        logger.info(f"Starting analysis {analysis_id} for file: {file.filename}")
        
        # Update analysis status to processing
        AnalysisService.update_analysis_status(session, analysis_id, "processing")
        session.commit()
        
        # Process the financial document
        analysis_result = run_crew(query=query, file_path=file_path)
        
        # Complete the analysis - with better error handling
        logger.info(f"Saving analysis result of length: {len(analysis_result)}")
        logger.info("Calling AnalysisService.complete_analysis")
        completion_success = AnalysisService.complete_analysis(
            session=session,
            analysis_id=analysis_id,
            result=analysis_result,
            summary=None,  # You could add logic to extract a summary
            confidence_score=None,  # You could add confidence scoring
            key_insights_count=None  # You could count key insights
        )
        
        # Mark document as processed
        DocumentService.mark_document_processed(session, document_id)
        
        # Log completion
        AnalysisHistoryService.log_action(
            session=session,
            analysis_id=analysis_id,
            action="completed",
            user_id=user_id,
            details="Analysis completed successfully"
        )
        session.commit()
        
        if not completion_success:
            logger.error(f"Failed to complete analysis {analysis_id}")
            raise HTTPException(status_code=500, detail="Failed to save analysis results")
        
        logger.info(f"Analysis {analysis_id} completed successfully")
        
        return {
            "status": "success",
            "analysis_id": analysis_id,
            "document_id": document_id,
            "user_id": user_id,
            "file_info": {
                "filename": file.filename,
                "size_mb": round(file_size / 1024 / 1024, 2),
                "processed_at": datetime.utcnow().isoformat()
            },
            "query": query,
            "analysis": analysis_result,
            "metadata": {
                "processing_id": file_id,
                "file_type": "PDF",
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "kept_file": keep_file or KEEP_UPLOADED_FILES
            }
        }
        
    except HTTPException:
        # Mark analysis as failed if it was created
        if analysis_id and session:
            try:
                AnalysisService.fail_analysis(session, analysis_id, "HTTP Exception occurred")
                session.commit()
            except:
                pass
        raise  # Re-raise HTTP exceptions as-is
        
    except Exception as e:
        logger.error(f"Unexpected error processing file: {e}")
        
        # Mark analysis as failed if it was created
        if analysis_id and session:
            try:
                AnalysisService.fail_analysis(session, analysis_id, str(e))
                session.commit()
            except:
                pass
                
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Internal server error during document processing",
                "details": str(e),
                "analysis_id": analysis_id,
                "document_id": document_id
            }
        )
    
    finally:
        # Clean up uploaded file if not keeping it
        if file_path and os.path.exists(file_path):
            if not (keep_file or KEEP_UPLOADED_FILES):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup file {file_path}: {cleanup_error}")
            else:
                # Update document to reflect persistent storage
                if document_id and session:
                    try:
                        DocumentService.set_document_persistent_storage(session, document_id, True)
                        session.commit()
                    except:
                        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )

# Additional API endpoints for data retrieval

@app.get("/analysis/history", response_model=dict)
async def get_analysis_history(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None,
    session: Session = Depends(get_db_session)
):
    """Get analysis history for the current user session"""
    try:
        # For now, we create a new user session since we don't have session persistence
        # In a real app, you'd get the user from session/JWT token
        user_id = get_or_create_user(session, request)
        
        analyses, total_count = AnalysisService.get_user_analyses(
            session=session,
            user_id=user_id,
            page=page,
            page_size=page_size,
            status_filter=status
        )
        
        # Convert to response format
        analysis_responses = []
        for analysis in analyses:
            # Get document info
            document = DocumentService.get_document_by_id(session, analysis.document_id)
            document_info = DocumentResponse.from_orm(document) if document else None
            
            analysis_resp = AnalysisResponse.from_orm(analysis)
            analysis_resp.document = document_info
            analysis_responses.append(analysis_resp)
        
        has_more = (page * page_size) < total_count
        
        return {
            "analyses": [resp.dict() for resp in analysis_responses],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "has_more": has_more,
                "total_pages": (total_count + page_size - 1) // page_size
            },
            "filters": {
                "status": status
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting analysis history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/{analysis_id}", response_model=dict)
async def get_analysis_by_id(
    analysis_id: str,
    request: Request,
    session: Session = Depends(get_db_session)
):
    """Get specific analysis by ID"""
    try:
        analysis = AnalysisService.get_analysis_by_id(session, analysis_id)
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Get document info
        document = DocumentService.get_document_by_id(session, analysis.document_id)
        document_info = DocumentResponse.from_orm(document) if document else None
        
        # Log the view action
        user_id = get_or_create_user(session, request)
        AnalysisHistoryService.log_action(
            session=session,
            analysis_id=analysis_id,
            action="viewed",
            user_id=user_id,
            ip_address=get_client_info(request)['ip_address']
        )
        session.commit()
        
        analysis_resp = AnalysisResponse.from_orm(analysis)
        analysis_resp.document = document_info
        
        return {
            "analysis": analysis_resp.dict(),
            "document": document_info.dict() if document_info else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents", response_model=dict)
async def get_user_documents(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    session: Session = Depends(get_db_session)
):
    """Get user's uploaded documents"""
    try:
        user_id = get_or_create_user(session, request)
        
        documents, total_count = DocumentService.get_user_documents(
            session=session,
            user_id=user_id,
            page=page,
            page_size=page_size
        )
        
        document_responses = [DocumentResponse.from_orm(doc) for doc in documents]
        has_more = (page * page_size) < total_count
        
        return {
            "documents": [resp.dict() for resp in document_responses],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "has_more": has_more,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/analysis/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    request: Request,
    session: Session = Depends(get_db_session)
):
    """Delete a specific analysis"""
    try:
        user_id = get_or_create_user(session, request)
        
        # Check if analysis exists and belongs to user
        analysis = AnalysisService.get_analysis_by_id(session, analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if analysis.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this analysis")
        
        # Log the deletion action before deleting
        AnalysisHistoryService.log_action(
            session=session,
            analysis_id=analysis_id,
            action="deleted",
            user_id=user_id,
            details=f"Analysis deleted: {analysis.query[:100]}...",
            ip_address=get_client_info(request)['ip_address']
        )
        
        # Delete the analysis
        success = AnalysisService.delete_analysis(session, analysis_id, user_id)
        
        if success:
            session.commit()
            return {"message": "Analysis deleted successfully", "analysis_id": analysis_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete analysis")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics", response_model=dict)
async def get_analysis_statistics(
    request: Request,
    session: Session = Depends(get_db_session)
):
    """Get analysis statistics for the current user"""
    try:
        user_id = get_or_create_user(session, request)
        
        # Get user-specific statistics
        user_stats = AnalysisService.get_analysis_statistics(session, user_id)
        
        # Get overall system statistics (optional)
        system_stats = AnalysisService.get_analysis_statistics(session)
        
        return {
            "user_statistics": user_stats,
            "system_statistics": system_stats,
            "database_info": get_database_manager().get_database_info()
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analysis/{analysis_id}/status")
async def get_analysis_status(
    analysis_id: str,
    session: Session = Depends(get_db_session)
):
    """Get the current status of an analysis (useful for polling during processing)"""
    try:
        analysis = AnalysisService.get_analysis_by_id(session, analysis_id)
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Calculate progress percentage based on status
        progress_map = {
            "pending": 0,
            "processing": 50,
            "completed": 100,
            "failed": 100
        }
        
        status_response = AnalysisStatusResponse(
            status=analysis.status,
            message=f"Analysis is {analysis.status}",
            analysis_id=analysis_id,
            progress_percentage=progress_map.get(analysis.status, 0)
        )
        
        return status_response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# File management and maintenance endpoints
from file_manager import get_file_manager

@app.post("/admin/maintenance")
async def run_maintenance(session: Session = Depends(get_db_session)):
    """Run file system maintenance (admin only)"""
    try:
        file_manager = get_file_manager()
        results = file_manager.perform_maintenance()
        
        return {
            "status": "success",
            "maintenance_results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during maintenance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/storage-stats")
async def get_storage_statistics():
    """Get storage usage statistics"""
    try:
        file_manager = get_file_manager()
        stats = file_manager.get_storage_statistics()
        
        return {
            "storage_statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
