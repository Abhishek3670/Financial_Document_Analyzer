from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import asyncio
import logging
from pathlib import Path
import magic

from crewai import Crew, Process
from agents import financial_analyst
from task import analyze_financial_document

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial Document Analyzer",
    description="AI-powered financial document analysis system",
    version="1.0.0"
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
            agents=[financial_analyst],
            tasks=[analyze_financial_document],
            process=Process.sequential,
            verbose=True
        )

        result = financial_crew.kickoff({'query': query, 'file_path': file_path})
        return str(result)
        
    except Exception as e:
        logger.error(f"Error running crew: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Analysis processing error: {str(e)}"
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Financial Document Analyzer API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "file_upload": "available",
            "ai_analysis": "available"
        }
    }

@app.post("/analyze")
async def analyze_document_endpoint(
    file: UploadFile = File(..., description="PDF file to analyze (max 50MB)"),
    query: str = Form(
        default="Provide a comprehensive financial analysis of this document", 
        description="Specific analysis query or instructions"
    )
):
    """Analyze financial document and provide comprehensive investment recommendations"""
    
    file_id = str(uuid.uuid4())
    file_path = None
    
    try:
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
        
        # Save uploaded file with unique name
        file_path = os.path.join(UPLOAD_DIR, f"financial_document_{file_id}.pdf")
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File saved: {file_path}, size: {file_size} bytes")
        
        # Validate and sanitize query
        if not query or not query.strip():
            query = "Provide a comprehensive financial analysis of this document"
        
        # Limit query length to prevent abuse
        query = query.strip()[:1000]  # Max 1000 characters
        
        logger.info(f"Starting analysis for file: {file.filename}")
        
        # Process the financial document
        analysis_result = run_crew(query=query, file_path=file_path)
        
        logger.info("Analysis completed successfully")
        
        return {
            "status": "success",
            "file_info": {
                "filename": file.filename,
                "size_mb": round(file_size / 1024 / 1024, 2),
                "processed_at": file_id
            },
            "query": query,
            "analysis": analysis_result,
            "metadata": {
                "processing_id": file_id,
                "file_type": "PDF",
                "analysis_timestamp": "completed"
            }
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
        
    except Exception as e:
        logger.error(f"Unexpected error processing file: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Internal server error during document processing",
                "details": str(e),
                "processing_id": file_id
            }
        )
    
    finally:
        # Clean up uploaded file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup file {file_path}: {cleanup_error}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
