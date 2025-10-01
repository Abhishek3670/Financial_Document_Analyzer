# Authentication imports
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import uuid
import time
import logging
from pathlib import Path
import magic
from datetime import datetime
from typing import List, Optional, Dict, Any

from crewai import Crew, Process

from typing import List, Optional

from crewai import Crew, Process
from backend.core.agents import (
    financial_analyst, data_extractor, investment_analyst, risk_analyst,
    document_verifier, investment_specialist, risk_assessor, report_coordinator
)
from backend.core.task import (
    comprehensive_financial_analysis,
    document_verification_task, financial_analysis_task,
    investment_analysis_task, risk_assessment_task, report_synthesis_task
)

# Database imports
from backend.core.database import init_database, get_db_session, get_database_manager
from backend.services.services import UserService, DocumentService, AnalysisService, AnalysisHistoryService
from backend.models.models import (
    User,
    Document,
    Analysis,
    AnalysisResponse, DocumentResponse, AnalysisHistoryResponse,
    CreateAnalysisRequest, AnalysisStatusResponse,
    # Authentication models
    UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm,
    UserProfileUpdate
)

# Authentication imports
from backend.auth.auth import auth_service
from backend.auth.auth_middleware import (
    get_current_user, get_current_active_user,
    get_optional_user, get_user_or_session
)

# Import Redis cache
from backend.utils.redis_cache import cache_result, cache_llm_result, cache_analysis_result

# Setup logging
import logging.handlers
from datetime import datetime

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Generate a daily log filename (one file per day) in format: log-YYYYMMDD
current_date = datetime.now().strftime("%Y%m%d")
log_filename = f"logs/log-{current_date}.log"

# Configure logging to both file and console
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Create file handler with daily rotation
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Add separator line to distinguish new logs from old ones
separator = "=" * 80
logger.info(f"\n{separator}\nApplication started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{separator}\n")

# Agent performance tracking
crew_performance_metrics = {}

def track_crew_performance(crew_name, start_time):
    """Track crew execution performance"""
    execution_time = time.time() - start_time
    if crew_name not in crew_performance_metrics:
        crew_performance_metrics[crew_name] = []
    crew_performance_metrics[crew_name].append(execution_time)
    logger.info(f"Crew {crew_name} completed in {execution_time:.2f} seconds")

def get_crew_performance_summary():
    """Get performance summary for all crews"""
    summary = {}
    for crew_name, times in crew_performance_metrics.items():
        if times:
            summary[crew_name] = {
                "total_executions": len(times),
                "average_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "total_time": sum(times)
            }
    return summary

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
OUTPUT_DIR = "output"
KEEP_UPLOADED_FILES = os.getenv('KEEP_UPLOADED_FILES', 'false').lower() == 'true'

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_client_info(request: Request) -> dict:
    """Extract client information from request"""
    return {
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent', None)
    }

def get_or_create_user(session: Session, request: Request) -> str:
    """Get or create user session"""
    # Try to get user from authenticated session first
    try:
        # Check for Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user = auth_service.get_current_user(session, token)
            if user:
                return user.id
    except Exception as e:
        logger.debug(f"Failed to get user from auth token: {e}")
    
    # Try to get session_id from headers or cookies
    session_id = request.headers.get("X-Session-ID") or request.cookies.get("session_id")
    
    if session_id:
        # Try to find existing user with this session_id
        user = UserService.get_user_by_session_id(session, session_id)
        if user:
            # Update last activity
            user.last_activity = datetime.utcnow()
            session.commit()
            return user.id
    
    # Create new session user
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

@cache_analysis_result(ttl=14400)  # Cache for 4 hours
def run_crew(query: str, file_path: str) -> str:
    """Run the CrewAI crew for financial analysis"""
    start_time = time.time()
    crew_name = "original_crew"
    try:
        financial_crew = Crew(
            agents=[financial_analyst, data_extractor, investment_analyst, risk_analyst],
            tasks=[comprehensive_financial_analysis],
            process=Process.sequential,
            verbose=True
        )

        result = financial_crew.kickoff({'query': query, 'file_path': file_path})
        
        # Track performance
        track_crew_performance(crew_name, start_time)
        
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
                from backend.utils.tools import financial_document_tool
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
        # Track performance even on error
        track_crew_performance(crew_name, start_time)
        logger.error(f"Error running crew: {e}")
        # Generate a fallback analysis in case of complete failure
        try:
            from backend.utils.tools import financial_document_tool
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

@cache_analysis_result(ttl=14400)  # Cache for 4 hours
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

@cache_analysis_result(ttl=14400)  # Cache for 4 hours
def run_enhanced_multi_agent_crew(query: str, file_path: str) -> str:
    """Run the enhanced CrewAI crew with specialized agents for comprehensive financial analysis"""
    start_time = time.time()
    crew_name = "enhanced_crew"
    try:
        logger.info("Starting enhanced multi-agent financial analysis workflow")
        
        # Create the enhanced crew with specialized agents and tasks
        enhanced_financial_crew = Crew(
            agents=[
                document_verifier,
                financial_analyst, 
                investment_specialist,
                risk_assessor,
                report_coordinator
            ],
            tasks=[
                document_verification_task,
                financial_analysis_task,
                investment_analysis_task,
                risk_assessment_task,
                report_synthesis_task
            ],
            process=Process.hierarchical,
            verbose=True,
            manager_llm=llm,
            memory=True,
            planning=True
        )

        # Execute the enhanced workflow
        result = enhanced_financial_crew.kickoff({
            "query": query, 
            "file_path": file_path
        })
        
        # Track performance
        track_crew_performance(crew_name, start_time)
        
        logger.info(f"Enhanced CrewAI workflow completed. Result type: {type(result)}")
        logger.info(f"Enhanced CrewAI result length: {len(str(result)) if result else 0}")
        logger.info(f"Enhanced CrewAI result preview: {str(result)[:200] if result else 'None'}")
        
        # Log performance metrics
        execution_time = time.time() - start_time
        logger.info(f"PERFORMANCE METRICS - Enhanced Crew: {execution_time:.2f}s")
        
        # Process the result from the enhanced workflow
        if result is None:
            result = "No analysis result was generated from the enhanced workflow. Please try again."
        elif hasattr(result, "raw"):
            result = str(result.raw)
        else:
            result = str(result)
            
        # Validate result quality
        if len(result.strip()) < 100:
            logger.warning(f"Enhanced CrewAI result appears incomplete: {result[:100]}")
            # Fall back to the original single-agent crew
            logger.info("Falling back to original crew configuration")
            return run_crew(query, file_path)
            
        return result
        
    except Exception as e:
        # Track performance even on error
        track_crew_performance(crew_name, start_time)
        execution_time = time.time() - start_time
        logger.error(f"Enhanced crew workflow error after {execution_time:.2f} seconds: {e}")
        logger.info("Falling back to original crew configuration due to error")
        # Fall back to the original crew configuration
        return run_crew(query, file_path)

@cache_analysis_result(ttl=14400)  # Cache for 4 hours
def run_parallel_multi_agent_crew(query: str, file_path: str) -> str:
    """Run an optimized parallel processing workflow with separate crews for different analysis tracks"""
    start_time = time.time()
    crew_name = "parallel_crew"
    try:
        logger.info("Starting parallel multi-agent financial analysis workflow")
        
        # First, run document verification (required for all other tasks)
        verification_start = time.time()
        verification_crew = Crew(
            agents=[document_verifier],
            tasks=[document_verification_task],
            process=Process.sequential,
            verbose=True,
            memory=True
        )
        
        # Execute document verification
        verification_result = verification_crew.kickoff({
            "query": query,
            "file_path": file_path
        })
        verification_time = time.time() - verification_start
        logger.info(f"Document verification completed in {verification_time:.2f} seconds")
        
        # Run financial analysis (required for investment and risk analysis)
        financial_start = time.time()
        financial_crew = Crew(
            agents=[financial_analyst],
            tasks=[financial_analysis_task],
            process=Process.sequential,
            verbose=True,
            memory=True
        )
        
        # Execute financial analysis
        financial_result = financial_crew.kickoff({
            "query": query,
            "file_path": file_path
        })
        financial_time = time.time() - financial_start
        logger.info(f"Financial analysis completed in {financial_time:.2f} seconds")
        
        # Run investment and risk analysis in parallel using ThreadPoolExecutor
        import concurrent.futures
        import threading
        
        def run_investment_analysis():
            investment_start = time.time()
            investment_crew = Crew(
                agents=[investment_specialist],
                tasks=[investment_analysis_task],
                process=Process.sequential,
                verbose=True,
                memory=True
            )
            result = investment_crew.kickoff({
                "query": query,
                "file_path": file_path
            })
            investment_time = time.time() - investment_start
            logger.info(f"Investment analysis completed in {investment_time:.2f} seconds")
            return result, investment_time
        
        def run_risk_analysis():
            risk_start = time.time()
            risk_crew = Crew(
                agents=[risk_assessor],
                tasks=[risk_assessment_task],
                process=Process.sequential,
                verbose=True,
                memory=True
            )
            result = risk_crew.kickoff({
                "query": query,
                "file_path": file_path
            })
            risk_time = time.time() - risk_start
            logger.info(f"Risk analysis completed in {risk_time:.2f} seconds")
            return result, risk_time
        
        # Execute investment and risk analysis in parallel
        parallel_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            investment_future = executor.submit(run_investment_analysis)
            risk_future = executor.submit(run_risk_analysis)
            
            investment_result, investment_time = investment_future.result(timeout=300)  # 5 minute timeout
            risk_result, risk_time = risk_future.result(timeout=300)  # 5 minute timeout
        parallel_time = time.time() - parallel_start
        logger.info(f"Parallel analyses completed in {parallel_time:.2f} seconds")
        
        # Finally, run report synthesis with all results
        synthesis_start = time.time()
        synthesis_crew = Crew(
            agents=[report_coordinator],
            tasks=[report_synthesis_task],
            process=Process.sequential,
            verbose=True,
            memory=True
        )
        
        # Execute report synthesis
        final_result = synthesis_crew.kickoff({
            "query": query,
            "file_path": file_path
        })
        synthesis_time = time.time() - synthesis_start
        logger.info(f"Report synthesis completed in {synthesis_time:.2f} seconds")
        
        execution_time = time.time() - start_time
        logger.info(f"Parallel multi-agent workflow completed in {execution_time:.2f} seconds")
        
        # Track performance
        track_crew_performance(crew_name, start_time)
        
        # Log detailed performance metrics
        logger.info(f"PERFORMANCE METRICS - Parallel Crew:")
        logger.info(f"  Total Execution Time: {execution_time:.2f}s")
        logger.info(f"  Document Verification: {verification_time:.2f}s")
        logger.info(f"  Financial Analysis: {financial_time:.2f}s")
        logger.info(f"  Investment Analysis: {investment_time:.2f}s")
        logger.info(f"  Risk Analysis: {risk_time:.2f}s")
        logger.info(f"  Parallel Analyses: {parallel_time:.2f}s")
        logger.info(f"  Report Synthesis: {synthesis_time:.2f}s")
        
        return final_result
        
    except Exception as e:
        # Track performance even on error
        track_crew_performance(crew_name, start_time)
        execution_time = time.time() - start_time
        logger.error(f"Parallel crew workflow error after {execution_time:.2f} seconds: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Analysis processing error: {str(e)}"
        )

@cache_analysis_result(ttl=14400)  # Cache for 4 hours
def run_dynamic_multi_agent_crew(query: str, file_path: str) -> str:
    """Run a dynamic multi-agent crew with agent selection based on document type and industry"""
    start_time = time.time()
    crew_name = "dynamic_crew"
    try:
        logger.info("Starting dynamic multi-agent financial analysis workflow")
        
        # First, read and classify the document
        from backend.utils.tools import financial_document_tool, document_classifier_tool
        
        # Read the document
        document_content = financial_document_tool._run(file_path)
        
        # Classify the document
        classification = document_classifier_tool._run(document_content)
        document_type = classification.get("document_type", "unknown")
        industry = classification.get("industry", "general")
        processing_speed = classification.get("processing_speed", "standard")
        
        logger.info(f"Document classified as: {document_type} in {industry} industry with {processing_speed} processing speed")
        
        # Create dynamic agents based on classification
        from backend.core.agents import create_dynamic_agents
        dynamic_agents = create_dynamic_agents(document_type, industry, processing_speed)
        
        # Create the crew with dynamic agents
        dynamic_financial_crew = Crew(
            agents=[
                dynamic_agents["document_verifier"],
                dynamic_agents["financial_analyst"], 
                dynamic_agents["investment_specialist"],
                dynamic_agents["risk_assessor"],
                dynamic_agents["report_coordinator"]
            ],
            tasks=[
                document_verification_task,
                financial_analysis_task,
                investment_analysis_task,
                risk_assessment_task,
                report_synthesis_task
            ],
            process=Process.hierarchical,
            verbose=True,
            manager_llm=llm,
            memory=True,
            planning=True
        )

        # Execute the dynamic workflow
        result = dynamic_financial_crew.kickoff({
            "query": query, 
            "file_path": file_path
        })
        
        # Track performance
        track_crew_performance(crew_name, start_time)
        
        execution_time = time.time() - start_time
        logger.info(f"Dynamic CrewAI workflow completed in {execution_time:.2f} seconds")
        logger.info(f"Dynamic CrewAI workflow completed. Result type: {type(result)}")
        logger.info(f"Dynamic CrewAI result length: {len(str(result)) if result else 0}")
        logger.info(f"Dynamic CrewAI result preview: {str(result)[:200] if result else 'None'}")
        
        # Process the result from the dynamic workflow
        if result is None:
            result = "No analysis result was generated from the dynamic workflow. Please try again."
        elif hasattr(result, "raw"):
            result = str(result.raw)
        else:
            result = str(result)
            
        # Validate result quality
        if len(result.strip()) < 100:
            logger.warning(f"Dynamic CrewAI result appears incomplete: {result[:100]}")
            # Fall back to the parallel crew configuration
            logger.info("Falling back to parallel crew configuration")
            return run_parallel_multi_agent_crew(query, file_path)
            
        return result
        
    except Exception as e:
        # Track performance even on error
        track_crew_performance(crew_name, start_time)
        execution_time = time.time() - start_time
        logger.error(f"Dynamic crew workflow error after {execution_time:.2f} seconds: {e}")
        logger.info("Falling back to parallel crew configuration due to error")
        # Fall back to the parallel crew configuration
        return run_parallel_multi_agent_crew(query, file_path)

def run_crew_with_mode(query: str, file_path: str, use_enhanced: bool = True) -> str:
    """Run crew analysis with only the parallel multi-agent approach as the single execution method"""
    # Always use the parallel multi-agent approach as the single execution method
    # All existing functions are preserved for backward compatibility
    return run_parallel_multi_agent_crew(query, file_path)

def compare_crew_performance(query: str, file_path: str) -> Dict[str, Any]:
    """Compare performance of different crew implementations"""
    performance_results = {}
    
    # Test original crew
    start_time = time.time()
    try:
        original_result = run_crew(query, file_path)
        original_time = time.time() - start_time
        performance_results["original"] = {
            "time": original_time,
            "success": True,
            "result_length": len(original_result) if original_result else 0
        }
    except Exception as e:
        performance_results["original"] = {
            "time": time.time() - start_time,
            "success": False,
            "error": str(e)
        }
    
    # Test enhanced crew
    start_time = time.time()
    try:
        enhanced_result = run_enhanced_multi_agent_crew(query, file_path)
        enhanced_time = time.time() - start_time
        performance_results["enhanced"] = {
            "time": enhanced_time,
            "success": True,
            "result_length": len(enhanced_result) if enhanced_result else 0
        }
    except Exception as e:
        performance_results["enhanced"] = {
            "time": time.time() - start_time,
            "success": False,
            "error": str(e)
        }
    
    # Test parallel crew
    start_time = time.time()
    try:
        parallel_result = run_parallel_multi_agent_crew(query, file_path)
        parallel_time = time.time() - start_time
        performance_results["parallel"] = {
            "time": parallel_time,
            "success": True,
            "result_length": len(parallel_result) if parallel_result else 0
        }
    except Exception as e:
        performance_results["parallel"] = {
            "time": time.time() - start_time,
            "success": False,
            "error": str(e)
        }
    
    # Calculate performance improvements
    if performance_results["original"]["success"] and performance_results["parallel"]["success"]:
        original_time = performance_results["original"]["time"]
        parallel_time = performance_results["parallel"]["time"]
        if original_time > 0:
            improvement = ((original_time - parallel_time) / original_time) * 100
            performance_results["improvement_percentage"] = improvement
    
    return performance_results

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
    background_tasks: BackgroundTasks,
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
        
        # Add the analysis task to background tasks
        background_tasks.add_task(
            process_analysis_background,
            analysis_id=analysis_id,
            document_id=document_id,
            query=query,
            file_path=file_path,
            user_id=user_id,
            keep_file=keep_file
        )
        
        # Return immediately with analysis ID for polling
        return {
            "status": "processing",
            "analysis_id": analysis_id,
            "document_id": document_id,
            "user_id": user_id,
            "file_info": {
                "filename": file.filename,
                "size_mb": round(file_size / 1024 / 1024, 2),
                "processed_at": datetime.utcnow().isoformat()
            },
            "query": query,
            "message": "Analysis started. Please poll the /analysis/{analysis_id}/status endpoint for progress.",
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
        # Don't clean up the file here since background task needs it
        # Cleanup will be handled in the background task
        pass

def process_analysis_background(
    analysis_id: str,
    document_id: str,
    query: str,
    file_path: str,
    user_id: str,
    keep_file: bool
):
    """Process the analysis in the background using a separate thread to avoid blocking"""
    # Create a new database session for the background task
    from backend.core.database import db_manager
    if not db_manager:
        from backend.core.database import init_database
        db_manager = init_database()
    
    session = db_manager.get_session()
    try:
        # Run the CrewAI analysis in a separate thread to avoid blocking
        import concurrent.futures
        import threading
        
        logger.info(f"Starting CrewAI analysis in thread: {threading.current_thread().name}")
        
        # Use a thread pool executor to run the CPU-intensive CrewAI task
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_crew_with_mode, query=query, file_path=file_path, use_enhanced=True)
            # Wait for completion with a timeout (increased to 15 minutes for complex financial analysis)
            analysis_result = future.result(timeout=900)  # 15 minutes timeout
        
        logger.info(f"CrewAI analysis completed in thread: {threading.current_thread().name}")
        # Convert CrewOutput to string before getting length
        result_str = str(analysis_result)
        logger.info(f"CrewAI result length: {len(result_str)}")
        
        # Complete the analysis - with better error handling
        logger.info("Calling AnalysisService.complete_analysis")
        # Convert CrewOutput to string before passing to complete_analysis
        result_str = str(analysis_result)
        completion_success = AnalysisService.complete_analysis(
            session=session,
            analysis_id=analysis_id,
            result=result_str,
            summary=None,  # You could add logic to extract a summary
            confidence_score=None,  # You could add confidence scoring
            key_insights_count=None  # You could count key insights
        )
        
        # Mark document as processed
        try:
            DocumentService.mark_document_processed(session, document_id)
        except Exception as doc_error:
            logger.error(f"Error marking document as processed: {doc_error}")
        
        # Log completion
        try:
            AnalysisHistoryService.log_action(
                session=session,
                analysis_id=analysis_id,
                action="completed",
                user_id=user_id,
                details="Analysis completed successfully"
            )
        except Exception as log_error:
            logger.error(f"Error logging analysis completion: {log_error}")
            
        try:
            session.commit()
        except Exception as commit_error:
            logger.error(f"Error committing session: {commit_error}")
            session.rollback()
        
        if not completion_success:
            logger.error(f"Failed to complete analysis {analysis_id}")
            try:
                AnalysisService.fail_analysis(session, analysis_id, "Failed to save analysis results")
                session.commit()
            except Exception as fail_error:
                logger.error(f"Error marking analysis as failed: {fail_error}")
        
        logger.info(f"Analysis {analysis_id} completed successfully")
        
    except concurrent.futures.TimeoutError:
        logger.error(f"Analysis {analysis_id} timed out")
        # Mark analysis as failed due to timeout
        try:
            AnalysisService.fail_analysis(session, analysis_id, "Analysis timed out after 10 minutes")
            session.commit()
        except Exception as db_error:
            logger.error(f"Failed to mark analysis as failed in database: {db_error}")
    except Exception as e:
        logger.error(f"Error in background analysis processing: {e}")
        error_message = str(e)
        
        # Make error messages more user-friendly
        if "insufficient_quota" in error_message or "429" in error_message:
            error_message = "OpenAI API quota exceeded. Please check your OpenAI plan and billing details. For more information, visit https://platform.openai.com/docs/guides/error-codes/api-errors"
        elif "rate limit" in error_message.lower():
            error_message = "API rate limit exceeded. Please try again later."
        elif "timeout" in error_message.lower():
            error_message = "Request timed out. Please try again with a simpler query or check your network connection."
        elif "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
            error_message = "Authentication failed. Please check your API credentials."
        elif "permission" in error_message.lower() or "forbidden" in error_message.lower():
            error_message = "Access forbidden. Please check your permissions."
        elif "not found" in error_message.lower():
            error_message = "Resource not found. The requested resource may have been deleted."
        elif "network" in error_message.lower() or "connection" in error_message.lower():
            error_message = "Network error. Please check your internet connection and try again."
        
        # Mark analysis as failed
        try:
            AnalysisService.fail_analysis(session, analysis_id, error_message)
            session.commit()
        except Exception as db_error:
            logger.error(f"Failed to mark analysis as failed in database: {db_error}")
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
                try:
                    DocumentService.set_document_persistent_storage(session, document_id, True)
                    session.commit()
                except Exception as storage_error:
                    logger.warning(f"Failed to update document storage status: {storage_error}")
        
        # Close the database session
        try:
            session.close()
        except Exception as close_error:
            logger.error(f"Error closing database session: {close_error}")

if __name__ == "__main__":
    import uvicorn
    # Add separator to logs when starting the application
    separator = "=" * 80
    logger.info(f"\n{separator}\nUvicorn server starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{separator}\n")
    
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
            try:
                # Get document info - make sure we're working with objects attached to the session
                # If analysis was retrieved from cache, it might be detached, so we re-fetch it to ensure it's attached
                if analysis not in session:
                    # Re-fetch analysis to ensure it's attached to session
                    analysis = session.query(Analysis).filter(Analysis.id == analysis.id).first()
                
                # Get document info - make sure document is also attached to session
                document = DocumentService.get_document_by_id(session, analysis.document_id)
                if not document or document not in session:
                    # Re-fetch document to ensure it's attached to session
                    document = session.query(Document).filter(Document.id == analysis.document_id).first()
                
                document_info = DocumentResponse.from_orm(document) if document else None
                
                # Create a dictionary representation instead of using from_orm to avoid issues
                analysis_dict = {
                    "id": analysis.id,
                    "user_id": analysis.user_id,
                    "document_id": analysis.document_id,
                    "original_filename": document.original_filename if document else None,
                    "query": analysis.query or "",
                    "analysis_type": analysis.analysis_type or "comprehensive",
                    "result": analysis.result or "",
                    "summary": analysis.summary,
                    "started_at": analysis.started_at.isoformat() if analysis.started_at else None,
                    "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                    "processing_time_seconds": analysis.processing_time_seconds,
                    "status": analysis.status,
                    "confidence_score": analysis.confidence_score,
                    "key_insights_count": analysis.key_insights_count,
                    "document": document_info.model_dump() if document_info else None
                }
                
                analysis_responses.append(analysis_dict)
            except Exception as analysis_error:
                logger.error(f"Error processing analysis {analysis.id}: {analysis_error}")
                # Continue with other analyses even if one fails
                continue
        
        has_more = (page * page_size) < total_count
        
        return {
            "analyses": analysis_responses,
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
        
        # Get document info - we need to make sure we're working with objects attached to the session
        # If analysis was retrieved from cache, it might be detached, so we re-fetch it to ensure it's attached
        if analysis not in session:
            # Re-fetch analysis to ensure it's attached to session
            analysis = session.query(Analysis).filter(Analysis.id == analysis_id).first()
            if not analysis:
                raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Get document info - make sure document is also attached to session
        document = DocumentService.get_document_by_id(session, analysis.document_id)
        if not document or document not in session:
            # Re-fetch document to ensure it's attached to session
            document = session.query(Document).filter(Document.id == analysis.document_id).first()
        
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
        
        # Convert to dict and include error_message if present
        response_dict = analysis_resp.model_dump()
        if hasattr(analysis, 'error_message') and analysis.error_message:
            response_dict['error_message'] = analysis.error_message
            
        return {
            "analysis": response_dict,
            "document": document_info.model_dump() if document_info else None
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
            "documents": [resp.model_dump() for resp in document_responses],
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

@app.get("/documents/search", response_model=dict)
async def search_user_documents(
    request: Request,
    search_term: str = None,
    page: int = 1,
    page_size: int = 10,
    session: Session = Depends(get_db_session)
):
    """Search user's uploaded documents"""
    try:
        user_id = get_or_create_user(session, request)
        
        documents, total_count = DocumentService.search_user_documents(
            session=session,
            user_id=user_id,
            search_term=search_term,
            page=page,
            page_size=page_size
        )
        
        document_responses = [DocumentResponse.from_orm(doc) for doc in documents]
        has_more = (page * page_size) < total_count
        
        return {
            "documents": [resp.model_dump() for resp in document_responses],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "has_more": has_more,
                "total_pages": (total_count + page_size - 1) // page_size
            },
            "search_term": search_term
        }
        
    except Exception as e:
        logger.error(f"Error searching user documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/document/classify", response_model=dict)
async def classify_document(
    file_path: str,
    session: Session = Depends(get_db_session)
):
    """Classify a financial document by type and industry"""
    try:
        from tools import financial_document_tool, document_classifier_tool
        
        # Read the document
        document_content = financial_document_tool._run(file_path)
        
        # Classify the document
        classification = document_classifier_tool._run(document_content)
        
        return {
            "classification": classification,
            "document_preview": document_content[:500] + "..." if len(document_content) > 500 else document_content
        }
    except Exception as e:
        logger.error(f"Document classification error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document classification failed: {str(e)}"
        )

@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    session: Session = Depends(get_db_session)
):
    """Delete a specific document"""
    try:
        user_id = get_or_create_user(session, request)
        
        # Check if document exists and belongs to user
        document = DocumentService.get_document_by_id(session, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")
        
        # Delete the document
        success = DocumentService.delete_document(session, document_id, user_id)
        
        if success:
            session.commit()
            return {"message": "Document deleted successfully", "document_id": document_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document")
            
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        # Rollback any changes in case of error
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

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
            details=f"Analysis deleted: {analysis.query[:100] if analysis.query else 'No query'}...",
            ip_address=get_client_info(request)['ip_address']
        )
        
        # Delete the analysis
        success = AnalysisService.delete_analysis(session, analysis_id, user_id)
        
        if success:
            session.commit()
            return {"message": "Analysis deleted successfully", "analysis_id": analysis_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete analysis due to database constraints")
            
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error deleting analysis {analysis_id}: {e}")
        # Rollback any changes in case of error
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete analysis: {str(e)}")

@app.get("/performance/agents", response_model=dict)
async def get_agent_performance():
    """Get performance metrics for all agents/crews"""
    try:
        # Get performance metrics from main.py
        summary = get_crew_performance_summary()
        return {
            "agent_performance": summary,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Agent performance metrics error: {e}")
        return {
            "agent_performance": {},
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/performance/tools", response_model=dict)
async def get_tool_performance():
    """Get performance metrics for all tools"""
    try:
        from backend.utils.tools import get_tool_performance_summary

        summary = get_tool_performance_summary()
        return {
            "tool_performance": summary,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Tool performance metrics error: {e}")
        return {
            "tool_performance": {},
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/performance/dashboard", response_model=dict)
async def performance_dashboard():
    """Get a comprehensive performance dashboard"""
    try:
        # Get agent performance metrics
        from backend.core.agents import get_agent_performance_summary, llm_observability
        agent_summary = get_agent_performance_summary()
        
        # Get tool performance metrics
        from tools import get_tool_performance_summary
        tool_summary = get_tool_performance_summary()
        
        # Get LLM metrics
        llm_metrics = llm_observability.get_metrics_summary()
        
        return {
            "agent_performance": agent_summary,
            "tool_performance": tool_summary,
            "llm_metrics": llm_metrics,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Performance dashboard error: {e}")
        return {
            "agent_performance": {},
            "tool_performance": {},
            "llm_metrics": {},
            "error": str(e),
            "timestamp": time.time()
        }

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
        
        return status_response.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# File management and maintenance endpoints
from backend.utils.file_manager import get_file_manager


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

@app.get("/performance/compare", response_model=dict)
async def compare_performance(
    query: str = "Performance comparison test",
    file_path: str = "test_file_path.pdf",
    session: Session = Depends(get_db_session)
):
    """Compare performance of different crew implementations"""
    try:
        logger.info(f"Performance comparison requested for query: {query}")
        results = compare_crew_performance(query, file_path)
        return results
    except Exception as e:
        logger.error(f"Performance comparison error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Performance comparison failed: {str(e)}"
        )

# Export functionality
from fastapi.responses import Response
from datetime import datetime
import html

@app.get("/analysis/{analysis_id}/export")
async def export_analysis_report(
    analysis_id: str,
    format: str = "html",
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Export analysis report in various formats"""
    try:
        # Get the analysis with the related document using a join to ensure document is loaded
        analysis = session.query(Analysis)\
                         .filter(Analysis.id == analysis_id)\
                         .first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Check if analysis object is valid
        if not hasattr(analysis, 'id'):
            raise HTTPException(status_code=500, detail="Invalid analysis object retrieved from database")
        
        # Check if user has access to this analysis
        if analysis.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied. You do not have permission to download this report.")
        
        # Get the document associated with this analysis
        document = session.query(Document)\
                         .filter(Document.id == analysis.document_id)\
                         .first()
        
        # Generate report content
        report_html = generate_analysis_report_html(analysis, document)
        
        if format == "html":
            response = Response(
                content=report_html,
                media_type="text/html",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''analysis_report_{analysis_id}.html"
                }
            )
            return response
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Only HTML format is supported.")
            
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status codes and messages
        raise
    except Exception as e:
        logger.error(f"Error exporting analysis {analysis_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate report. Please try again later.")

def generate_analysis_report_html(analysis, document=None) -> str:
    """Generate HTML report for analysis"""
    try:
        # Format the analysis result for display
        result_content = html.escape(str(analysis.result)) if analysis and analysis.result else "No analysis results available."
        
        # Get the original filename from the related document
        original_filename = document.original_filename if document and document.original_filename else "Unknown Document"
        
        # Format the created date
        created_at_str = analysis.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if analysis and analysis.started_at else "Unknown Date"
        
        html_template = f"""
        <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Financial Analysis Report</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .report-container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e0e0e0;
            }}
            .header h1 {{
                color: #2c3e50;
                margin-bottom: 10px;
            }}
            .header p {{
                color: #7f8c8d;
                margin: 5px 0;
            }}
            .section {{
                margin-bottom: 25px;
            }}
            .section h2 {{
                color: #34495e;
                border-left: 4px solid #3498db;
                padding-left: 15px;
                margin-bottom: 15px;
            }}
            .meta-info {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .meta-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
            }}
            .meta-label {{
                font-weight: bold;
                color: #555;
            }}
            .analysis-content {{
                background: #fff;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 20px;
                white-space: pre-wrap;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.5;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
                color: #7f8c8d;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="header">
                <h1>Financial Analysis Report</h1>
                <p>Generated by Wingily Financial Analyzer</p>
                <p>Report ID: {analysis.id}</p>
            </div>
            
            <div class="section">
                <h2>Analysis Summary</h2>
                <div class="meta-info">
                    <div class="meta-row">
                        <span class="meta-label">Document:</span>
                        <span>{html.escape(original_filename)}</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Analysis Date:</span>
                        <span>{created_at_str}</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Status:</span>
                        <span style="color: {'green' if analysis.status == 'completed' else 'orange'};">
                            {analysis.status.title() if analysis.status else 'Unknown'}
                        </span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Query:</span>
                        <span>{html.escape(analysis.query or 'General financial analysis')}</span>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Analysis Results</h2>
                <div class="analysis-content">
{result_content}
                </div>
            </div>
            
            <div class="footer">
                <p>This report was generated automatically by the Wingily Financial Document Analyzer.</p>
                <p>Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
        return html_template
    except Exception as e:
        logger.error(f"Error generating HTML report: {e}", exc_info=True)
        # Return a simple error report
        error_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error Generating Report</title>
        </head>
        <body>
            <h1>Error Generating Report</h1>
            <p>An error occurred while generating the report: {str(e)}</p>
            <p>Please try again later.</p>
        </body>
        </html>
        """
        return error_template

def save_analysis_report(analysis, document=None) -> str:
    """Generate and save HTML report to output folder"""
    try:
        # Generate the report content
        report_html = generate_analysis_report_html(analysis, document)
        
        # Create filename
        filename = f"analysis_report_{analysis.id}.html"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_html)
        
        logger.info(f"Saved analysis report to: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error saving analysis report: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

# LLM Observability endpoint
@app.get("/metrics/llm", response_model=dict)
async def get_llm_metrics(current_user: User = Depends(get_current_user)):
    """Get LLM observability metrics"""
    try:
        from backend.core.agents import get_llm_metrics

        metrics = get_llm_metrics()
        
        return {
            "status": "success",
            "data": metrics,
            "user_id": current_user.id
        }
    except Exception as e:
        logger.error(f"Failed to retrieve LLM metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve LLM metrics: {str(e)}"
        )

# Redis Cache endpoints
@app.get("/cache/stats", response_model=dict)
async def get_cache_stats(current_user: User = Depends(get_current_user)):
    """Get Redis cache statistics"""
    try:
        from backend.utils.redis_cache import redis_cache
        stats = redis_cache.get_stats()
        
        return {
            "status": "success",
            "data": stats,
            "user_id": current_user.id
        }
    except Exception as e:
        logger.error(f"Failed to retrieve cache stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cache stats: {str(e)}"
        )

@app.post("/cache/invalidate", response_model=dict)
async def invalidate_cache(
    cache_type: str = Form(...),
    pattern: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Invalidate cache entries"""
    try:
        from backend.utils.redis_cache import redis_cache, invalidate_analysis_cache, invalidate_llm_cache
        
        if cache_type == "analysis":
            invalidate_analysis_cache()
        elif cache_type == "llm":
            invalidate_llm_cache()
        elif cache_type == "pattern" and pattern:
            count = redis_cache.flush_pattern(pattern)
            return {
                "status": "success",
                "message": f"Invalidated {count} cache entries matching pattern: {pattern}",
                "user_id": current_user.id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cache_type. Use 'analysis', 'llm', or 'pattern' with pattern parameter"
            )
        
        return {
            "status": "success",
            "message": f"Cache invalidated for type: {cache_type}",
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )
