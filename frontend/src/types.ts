// Enhanced types to match the new database-integrated backend

export interface AnalysisResponse {
  status: string;
  analysis_id: string;
  document_id: string;
  user_id: string;
  file_info: {
    filename: string;
    size_mb: number;
    processed_at: string;
  };
  query: string;
  analysis: string;
  metadata: {
    processing_id: string;
    file_type: string;
    analysis_timestamp: string;
    kept_file: boolean;
  };
}

export interface DocumentResponse {
  id: string;
  user_id: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  upload_timestamp: string;
  is_processed: boolean;
  is_stored_permanently: boolean;
}

export interface AnalysisHistoryItem {
  id: string;
  user_id: string;
  document_id: string;
  query: string;
  analysis_type: string;
  result: string;
  summary?: string;
  started_at: string;
  completed_at?: string;
  processing_time_seconds?: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  confidence_score?: number;
  key_insights_count?: number;
  document?: DocumentResponse;
}

export interface AnalysisHistoryResponse {
  analyses: AnalysisHistoryItem[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    has_more: boolean;
    total_pages: number;
  };
  filters: {
    status?: string;
  };
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    has_more: boolean;
    total_pages: number;
  };
}

export interface UserStatistics {
  total_analyses: number;
  completed_analyses: number;
  failed_analyses: number;
  pending_analyses: number;
  success_rate: number;
  average_processing_time_seconds: number;
}

export interface SystemStatistics {
  total_analyses: number;
  completed_analyses: number;
  failed_analyses: number;
  pending_analyses: number;
  success_rate: number;
  average_processing_time_seconds: number;
}

export interface StatisticsResponse {
  user_statistics: UserStatistics;
  system_statistics: SystemStatistics;
  database_info: {
    type: string;
    file?: string;
    size_bytes?: number;
    size_mb?: number;
  };
}

export interface AnalysisStatusResponse {
  status: string;
  message: string;
  analysis_id?: string;
  progress_percentage?: number;
}

export interface StorageStatistics {
  storage_statistics: {
    temporary_files: {
      count: number;
      size_bytes: number;
      size_mb: number;
    };
    persistent_files: {
      count: number;
      size_bytes: number;
      size_mb: number;
    };
    total_size_mb: number;
  };
  timestamp: string;
}

export interface ApiError {
  error: string;
  details?: string;
  processing_id?: string;
  analysis_id?: string;
  document_id?: string;
}

// Request types
export interface AnalyzeRequest {
  file: File;
  query: string;
  keep_file?: boolean;
}

// UI State types
export interface LoadingState {
  isLoading: boolean;
  progress?: number;
  message?: string;
}

export interface PaginationState {
  page: number;
  pageSize: number;
  totalCount: number;
  hasMore: boolean;
}

export interface FilterState {
  status?: string;
  search?: string;
  dateRange?: {
    start: string;
    end: string;
  };
}
