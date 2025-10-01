"""
Database service layer for Financial Document Analyzer
Provides CRUD operations and business logic for all models
"""
import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
import logging
from typing import List, Tuple, Optional

from backend.models.models import User, Document, Analysis, AnalysisHistory
from backend.models.models import DocumentResponse, AnalysisResponse, AnalysisHistoryResponse
from backend.core.database import get_database_manager

# Import Redis cache
from backend.utils.redis_cache import cache_result, cache_database_query

logger = logging.getLogger(__name__)

class UserService:
    """Enhanced UserService with authentication support"""
    
    @staticmethod
    @cache_database_query(table="users", ttl=1800)  # Cache for 30 minutes
    def get_user_by_id(session: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return session.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    @cache_database_query(table="users", ttl=1800)  # Cache for 30 minutes
    def get_user_by_session_id(session: Session, session_id: str) -> Optional[User]:
        """Get user by session ID"""
        return session.query(User).filter(User.session_id == session_id).first()
    
    @staticmethod
    @cache_database_query(table="users", ttl=1800)  # Cache for 30 minutes
    def get_user_by_email(session: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return session.query(User).filter(User.email == email).first()
    
    @staticmethod
    @cache_database_query(table="users", ttl=1800)  # Cache for 30 minutes
    def get_user_by_username(session: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return session.query(User).filter(User.username == username).first()
    
    @staticmethod
    def create_user(session: Session, ip_address: str = None, user_agent: str = None) -> User:
        """Create a new user session (backward compatibility)"""
        try:
            user = User(ip_address=ip_address, user_agent=user_agent)
            session.add(user)
            session.flush()  # Get ID without committing
            logger.info(f"Created new user session: {user.id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    @staticmethod
    def update_user_activity(session: Session, user_id: str) -> bool:
        """Update user's last activity timestamp"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.last_activity = datetime.now()
                session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
            return False
    
    @staticmethod
    def update_user_login_time(session: Session, user: User) -> bool:
        """Update user's last login time"""
        try:
            user.last_login = datetime.now()
            user.last_activity = datetime.now()
            session.flush()
            return True
        except Exception as e:
            logger.error(f"Error updating user login time: {e}")
            return False
    
    @staticmethod
    def deactivate_user(session: Session, user_id: str) -> bool:
        """Deactivate a user account"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = False
                session.flush()
                logger.info(f"User deactivated: {user.email or user.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return False
    
    @staticmethod
    def reactivate_user(session: Session, user_id: str) -> bool:
        """Reactivate a user account"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = True
                session.flush()
                logger.info(f"User reactivated: {user.email or user.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error reactivating user: {e}")
            return False
    
    @staticmethod
    @cache_database_query(table="users", ttl=300)  # Cache for 5 minutes
    def get_authenticated_users(session: Session, limit: int = None) -> List[User]:
        """Get all authenticated users (users with email and password)"""
        query = session.query(User).filter(
            User.email.isnot(None),
            User.password_hash.isnot(None)
        ).order_by(User.created_at.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    @staticmethod
    @cache_database_query(table="users", ttl=300)  # Cache for 5 minutes
    def get_session_users(session: Session, limit: int = None) -> List[User]:
        """Get all session-only users (users without email/password)"""
        query = session.query(User).filter(
            User.email.is_(None),
            User.password_hash.is_(None)
        ).order_by(User.created_at.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    @staticmethod
    def cleanup_inactive_users(session: Session, days: int = 30) -> int:
        """Clean up users inactive for specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Only cleanup session users (not authenticated users)
            inactive_users = session.query(User).filter(
                User.last_activity < cutoff_date,
                User.email.is_(None),  # Only session users
                User.password_hash.is_(None)
            ).all()
            
            count = len(inactive_users)
            for user in inactive_users:
                # Delete related documents and analyses through cascade
                session.delete(user)
            
            logger.info(f"Cleaned up {count} inactive session users")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up inactive users: {e}")
            return 0
    
    @staticmethod
    @cache_result(prefix="user_stats", ttl=600)  # Cache for 10 minutes
    def get_user_stats(session: Session) -> dict:
        """Get user statistics"""
        try:
            total_users = session.query(User).count()
            authenticated_users = session.query(User).filter(
                User.email.isnot(None)
            ).count()
            session_users = total_users - authenticated_users
            active_users = session.query(User).filter(User.is_active == True).count()
            return {
                "total_users": total_users,
                "authenticated_users": authenticated_users,
                "session_users": session_users,
                "active_users": active_users
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

class DocumentService:
    """Service for document operations"""
    
    @staticmethod
    def create_document(
        session: Session,
        user_id: str,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int,
        file_type: str = "PDF",
        mime_type: str = "application/pdf",
        file_content: bytes = None
    ) -> Document:
        """Create a new document record"""
        try:
            # Calculate file hash if content provided
            file_hash = None
            if file_content:
                file_hash = hashlib.sha256(file_content).hexdigest()
            
            document = Document(
                user_id=user_id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                mime_type=mime_type,
                file_hash=file_hash
            )
            
            session.add(document)
            session.flush()
            logger.info(f"Created document record: {document.id} for user: {user_id}")
            return document
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    @staticmethod
    @cache_database_query(table="documents", ttl=1800)  # Cache for 30 minutes
    def get_document_by_id(session: Session, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        return session.query(Document).filter(Document.id == document_id).first()
    
    @staticmethod
    @cache_database_query(table="documents", ttl=600)  # Cache for 10 minutes
    def get_user_documents(
        session: Session, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 10
    ) -> Tuple[List[Document], int]:
        """Get user's documents with pagination"""
        try:
            offset = (page - 1) * page_size
            
            query = session.query(Document).filter(Document.user_id == user_id)
            total_count = query.count()
            
            documents = query.order_by(desc(Document.upload_timestamp))\
                           .offset(offset)\
                           .limit(page_size)\
                           .all()
            
            return documents, total_count
        except Exception as e:
            logger.error(f"Error getting user documents: {e}")
            return [], 0
    
    @staticmethod
    @cache_database_query(table="documents", ttl=1800)  # Cache for 30 minutes
    def find_duplicate_documents(session: Session, file_hash: str) -> List[Document]:
        """Find documents with the same hash"""
        if not file_hash:
            return []
        return session.query(Document).filter(Document.file_hash == file_hash).all()
    
    @staticmethod
    def mark_document_processed(session: Session, document_id: str) -> bool:
        """Mark document as processed"""
        try:
            document = session.query(Document).filter(Document.id == document_id).first()
            if document:
                document.is_processed = True
                session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking document as processed: {e}")
            return False
    
    @staticmethod
    def set_document_persistent_storage(session: Session, document_id: str, is_permanent: bool) -> bool:
        """Set document persistent storage flag"""
        try:
            document = session.query(Document).filter(Document.id == document_id).first()
            if document:
                document.is_stored_permanently = is_permanent
                session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting document storage flag: {e}")
            return False

    @staticmethod
    def delete_document(session: Session, document_id: str, user_id: str) -> bool:
        """Delete document (with user verification)"""
        try:
            # First verify the document exists and belongs to the user
            document = session.query(Document).filter(
                and_(Document.id == document_id, Document.user_id == user_id)
            ).first()
            
            if not document:
                logger.warning(f"Attempt to delete non-existent document {document_id} by user {user_id}")
                return False
            
            # Log the deletion attempt
            logger.info(f"Deleting document {document_id} for user {user_id}")
            
            # Explicitly delete related analyses first to avoid foreign key constraint violations
            related_analyses = session.query(Analysis).filter(Analysis.document_id == document_id).all()
            for analysis in related_analyses:
                # First delete related history records
                history_records = session.query(AnalysisHistory).filter(
                    AnalysisHistory.analysis_id == analysis.id
                ).all()
                for record in history_records:
                    session.delete(record)
                session.delete(analysis)
            
            logger.info(f"Deleted {len(related_analyses)} related analyses for document {document_id}")
            
            # Now delete the document
            session.delete(document)
            session.flush()
            
            logger.info(f"Successfully deleted document: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    @staticmethod
    @cache_database_query(table="documents", ttl=600)  # Cache for 10 minutes
    def search_user_documents(
        session: Session, 
        user_id: str,
        search_term: str = None,
        page: int = 1, 
        page_size: int = 10
    ) -> Tuple[List[Document], int]:
        """Search user's documents with pagination"""
        try:
            offset = (page - 1) * page_size
            
            query = session.query(Document).filter(Document.user_id == user_id)
            
            # Apply search filter if provided
            if search_term:
                search_filter = or_(
                    Document.original_filename.contains(search_term),
                )
                query = query.filter(search_filter)
            
            total_count = query.count()
            
            documents = query.order_by(desc(Document.upload_timestamp))\
                           .offset(offset)\
                           .limit(page_size)\
                           .all()
            
            return documents, total_count
        except Exception as e:
            logger.error(f"Error searching user documents: {e}")
            return [], 0

class AnalysisService:
    """Service for analysis operations"""
    
    @staticmethod
    def create_analysis(
        session: Session,
        user_id: str,
        document_id: str,
        query: str,
        analysis_type: str = "comprehensive"
    ) -> Analysis:
        """Create a new analysis record"""
        try:
            analysis = Analysis(
                user_id=user_id,
                document_id=document_id,
                query=query,
                analysis_type=analysis_type,
                status="pending",
                result=""  # Will be updated when processing completes
            )
            
            session.add(analysis)
            session.flush()
            logger.info(f"Created analysis record: {analysis.id}")
            return analysis
        except Exception as e:
            logger.error(f"Error creating analysis: {e}")
            raise
    
    @staticmethod
    def update_analysis_status(session: Session, analysis_id: str, status: str) -> bool:
        """Update analysis status"""
        try:
            analysis = session.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = status
                if status == "processing":
                    analysis.started_at = datetime.utcnow()
                session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating analysis status: {e}")
            return False
    
    @staticmethod
    def complete_analysis(
        session: Session,
        analysis_id: str,
        result: str,
        summary: str = None,
        confidence_score: float = None,
        key_insights_count: int = None
    ) -> bool:
        """Complete analysis with results"""
        try:
            analysis = session.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.result = result
                analysis.summary = summary
                analysis.completed_at = datetime.utcnow()
                analysis.status = "completed"
                analysis.confidence_score = confidence_score
                analysis.key_insights_count = key_insights_count
                
                # Calculate processing time
                if analysis.started_at:
                    processing_time = (analysis.completed_at - analysis.started_at).total_seconds()
                    analysis.processing_time_seconds = processing_time
                
                session.flush()
                
                # Generate and save report automatically
                try:
                    # Import here to avoid circular imports
                    from main import save_analysis_report
                    
                    # Get the document associated with this analysis
                    document = session.query(Document).filter(Document.id == analysis.document_id).first()
                    
                    # Generate and save the report
                    report_path = save_analysis_report(analysis, document)
                    if report_path:
                        logger.info(f"Automatically generated and saved report: {report_path}")
                    else:
                        logger.warning(f"Failed to automatically generate report for analysis: {analysis_id}")
                except Exception as report_error:
                    logger.error(f"Error generating automatic report for analysis {analysis_id}: {report_error}")
                
                logger.info(f"Completed analysis: {analysis_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error completing analysis: {e}")
            return False
    
    @staticmethod
    def fail_analysis(session: Session, analysis_id: str, error_message: str) -> bool:
        """Mark analysis as failed"""
        try:
            analysis = session.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = error_message
                analysis.completed_at = datetime.utcnow()
                session.flush()
                logger.info(f"Failed analysis: {analysis_id} - {error_message}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error failing analysis: {e}")
            return False
    
    @staticmethod
    def get_analysis_by_id(session: Session, analysis_id: str) -> Optional[Analysis]:
        """Get analysis by ID"""
        return session.query(Analysis).filter(Analysis.id == analysis_id).first()
    
    @staticmethod
    def get_user_analyses(
        session: Session,
        user_id: str,
        page: int = 1,
        page_size: int = 10,
        status_filter: str = None
    ) -> Tuple[List[Analysis], int]:
        """Get user's analyses with pagination and optional status filter"""
        try:
            offset = (page - 1) * page_size
            
            query = session.query(Analysis).filter(Analysis.user_id == user_id)
            
            if status_filter:
                query = query.filter(Analysis.status == status_filter)
            
            total_count = query.count()
            
            analyses = query.order_by(desc(Analysis.started_at))\
                          .offset(offset)\
                          .limit(page_size)\
                          .all()
            
            return analyses, total_count
        except Exception as e:
            logger.error(f"Error getting user analyses: {e}")
            return [], 0
    
    @staticmethod
    def delete_analysis(session: Session, analysis_id: str, user_id: str) -> bool:
        """Delete analysis (with user verification)"""
        try:
            # First verify the analysis exists and belongs to the user
            analysis = session.query(Analysis).filter(
                and_(Analysis.id == analysis_id, Analysis.user_id == user_id)
            ).first()
            
            if not analysis:
                logger.warning(f"Attempt to delete non-existent analysis {analysis_id} by user {user_id}")
                return False
            
            # Log the deletion attempt
            logger.info(f"Deleting analysis {analysis_id} for user {user_id}")
            
            # First delete related history records to avoid foreign key constraint violation
            history_records = session.query(AnalysisHistory).filter(
                AnalysisHistory.analysis_id == analysis_id
            ).all()
            
            for record in history_records:
                session.delete(record)
            
            logger.info(f"Deleted {len(history_records)} related history records for analysis {analysis_id}")
            
            # Now delete the analysis itself
            session.delete(analysis)
            session.flush()
            
            logger.info(f"Successfully deleted analysis: {analysis_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting analysis {analysis_id}: {e}")
            # Don't raise the exception here, just return False
            # The caller can decide how to handle the failure
            return False
    
    @staticmethod
    @cache_result(prefix="analysis_stats", ttl=600)  # Cache for 10 minutes
    def get_analysis_statistics(session: Session, user_id: str = None) -> dict:
        """Get analysis statistics"""
        try:
            base_query = session.query(Analysis)
            if user_id:
                base_query = base_query.filter(Analysis.user_id == user_id)
            
            total_analyses = base_query.count()
            completed_analyses = base_query.filter(Analysis.status == "completed").count()
            failed_analyses = base_query.filter(Analysis.status == "failed").count()
            pending_analyses = base_query.filter(Analysis.status == "pending").count()
            
            # Average processing time for completed analyses
            avg_processing_time = base_query.filter(
                and_(Analysis.status == "completed", Analysis.processing_time_seconds.isnot(None))
            ).with_entities(func.avg(Analysis.processing_time_seconds)).scalar()
            
            return {
                "total_analyses": total_analyses,
                "completed_analyses": completed_analyses,
                "failed_analyses": failed_analyses,
                "pending_analyses": pending_analyses,
                "success_rate": round((completed_analyses / total_analyses * 100), 2) if total_analyses > 0 else 0,
                "average_processing_time_seconds": round(avg_processing_time, 2) if avg_processing_time else 0
            }
        except Exception as e:
            logger.error(f"Error getting analysis statistics: {e}")
            return {}

class AnalysisHistoryService:
    """Service for analysis history operations"""
    
    @staticmethod
    def log_action(
        session: Session,
        analysis_id: str,
        action: str,
        user_id: str,
        details: str = None,
        ip_address: str = None
    ) -> AnalysisHistory:
        """Log an action in analysis history"""
        try:
            history_entry = AnalysisHistory(
                analysis_id=analysis_id,
                action=action,
                user_id=user_id,
                details=details,
                ip_address=ip_address
            )
            
            session.add(history_entry)
            session.flush()
            return history_entry
        except Exception as e:
            logger.error(f"Error logging analysis history: {e}")
            raise
    
    @staticmethod
    @cache_database_query(table="analysis_history", ttl=600)  # Cache for 10 minutes
    def get_analysis_history(
        session: Session,
        analysis_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[AnalysisHistory], int]:
        """Get history for a specific analysis"""
        try:
            offset = (page - 1) * page_size
            
            query = session.query(AnalysisHistory).filter(
                AnalysisHistory.analysis_id == analysis_id
            )
            
            total_count = query.count()
            
            history = query.order_by(desc(AnalysisHistory.timestamp))\
                          .offset(offset)\
                          .limit(page_size)\
                          .all()
            
            return history, total_count
        except Exception as e:
            logger.error(f"Error getting analysis history: {e}")
            return [], 0