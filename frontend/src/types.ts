// User types
export interface User {
  id: string;
  analysis_id?: string;
  query?: string;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_activity?: string;
  last_login?: string;
}

// Response types for components that need them
export interface AnalysisResponse {
  id: string;
  analysis_id?: string;
  query?: string;
  status: string;
  result: string;
  analysis?: string;
  created_at: string;
  completed_at?: string;
  document?: any;
  file_info?: {
    filename: string;
    size_mb: number;
    processed_at: string;
  };
  metadata?: {
    file_type: string;
    analysis_timestamp: string;
    processing_id: string;
    analysis_id?: string;
    query?: string;
    kept_file: boolean;
  };
}

// Filter and pagination states
export interface FilterState {
  status?: string;
  search?: string;
}

export interface PaginationState {
  page: number;
  pageSize: number;
  totalPages: number;
  totalCount: number;
}

// History response types
export interface AnalysisHistoryItem {
  id: string;
  analysis_id?: string;
  query: string;
  status: string;
  created_at: string;
  completed_at?: string;
  document?: {
    id: string;
    analysis_id?: string;
    query?: string;
    original_filename: string;
    file_size: number;
  };
}

export interface AnalysisHistoryResponse {
  analyses: AnalysisHistoryItem[];
  pagination: PaginationState;
  filters: FilterState;
}
