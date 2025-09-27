export interface AnalysisResponse {
  status: string;
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
  };
}

export interface ApiError {
  error: string;
  details?: string;
  processing_id?: string;
}
