import axios, { AxiosResponse } from 'axios';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Generate or retrieve session ID
const getSessionId = (): string => {
  let sessionId = localStorage.getItem('session_id');
  if (!sessionId) {
    sessionId = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('session_id', sessionId);
  }
  return sessionId;
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create a separate axios instance for health checks without custom headers
const healthApi = axios.create({
  baseURL: API_BASE_URL,
});

// Add auth token and session ID to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // Add session ID to headers
  const sessionId = getSessionId();
  if (sessionId) {
    config.headers['X-Session-ID'] = sessionId;
  }
  
  return config;
});

// Handle token expiration and other API errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
    }
    return Promise.reject(error);
  }
);

// Enhanced error extraction function
const extractErrorMessage = (error: any): string => {
  // Handle network errors
  if (!error.response) {
    return 'Network error. Please check your internet connection.';
  }
  
  // Handle different HTTP status codes
  const { status, data } = error.response;
  
  switch (status) {
    case 400:
      return data?.detail || 'Bad request. Please check your input.';
    case 401:
      return 'Authentication failed. Please log in again.';
    case 403:
      return 'Access forbidden. You do not have permission to perform this action.';
    case 404:
      return 'Resource not found.';
    case 429:
      return 'Rate limit exceeded. Please try again later.';
    case 500:
      return data?.detail || 'Internal server error. Please try again later.';
    case 502:
    case 503:
    case 504:
      return 'Service temporarily unavailable. Please try again later.';
    default:
      return data?.detail || `An error occurred (HTTP ${status}).`;
  }
};

// Types
export interface User {
  id: string;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  last_activity?: string;
  last_login?: string;
}

export interface RegisterData {
  email: string;
  password: string;
  confirm_password: string;
  first_name: string;
  last_name: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface ChangePasswordData {
  current_password: string;
  new_password: string;
  confirm_new_password: string;
}

export interface ProfileUpdateData {
  first_name?: string;
  last_name?: string;
  email?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface AnalysisResult {
  summary: string;
  key_insights: string[];
  recommendations: string[];
  risk_assessment: string;
  financial_metrics: Record<string, any>;
}

export interface Document {
  id: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  upload_date: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  is_processed: boolean;
  upload_timestamp: string;
  stored_filename?: string;
  file_path?: string;
  mime_type?: string;
  file_hash?: string;
  is_stored_permanently?: boolean;
}

export interface Analysis {
  id: string;
  document_id: string;
  original_filename?: string;
  query?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
  document?: Document;
}

export interface UploadResponse {
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
  analysis?: string; // This might not be available immediately
  message?: string; // New field for status message
  metadata: {
    processing_id: string;
    file_type: string;
    analysis_timestamp: string;
    kept_file: boolean;
  };
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    has_more: boolean;
    total_pages: number;
  };
}

// Authentication API
export const authAPI = {
  register: async (data: RegisterData): Promise<TokenResponse> => {
    try {
      const response = await api.post<TokenResponse>('/auth/register', {
        email: data.email,
        password: data.password,
        confirm_password: data.confirm_password,
        first_name: data.first_name,
        last_name: data.last_name,
        username: data.email, // Use email as username for now
      });

      // Store token and user data
      const { access_token, user } = response.data;
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('user_data', JSON.stringify(user));

      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  login: async (data: LoginData): Promise<TokenResponse> => {
    try {
      const response = await api.post<TokenResponse>('/auth/login', data);

      // Store token and user data
      const { access_token, user } = response.data;
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('user_data', JSON.stringify(user));

      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  logout: async (): Promise<void> => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      // Continue with logout even if API call fails
      console.warn('Logout API call failed, continuing with local cleanup');
    } finally {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
    }
  },

  getCurrentUser: async (): Promise<User> => {
    try {
      const response = await api.get<User>('/auth/me');
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  updateProfile: async (data: ProfileUpdateData): Promise<User> => {
    try {
      const response = await api.put<User>('/auth/profile', data);
      
      // Update stored user data
      localStorage.setItem('user_data', JSON.stringify(response.data));
      
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  changePassword: async (data: ChangePasswordData): Promise<{ message: string }> => {
    try {
      const response = await api.post('/auth/change-password', data);
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  requestPasswordReset: async (email: string): Promise<{ message: string; token?: string }> => {
    try {
      const response = await api.post('/auth/forgot-password', { email });
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    try {
      const response = await api.post('/auth/reset-password', {
        token,
        new_password: newPassword,
      });
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },
};

// Document Analysis API
export const documentAPI = {
  uploadAndAnalyze: async (
    file: File,
    query: string = 'Provide a comprehensive financial analysis of this document',
    keepFile: boolean = false,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('query', query);
      formData.append('keep_file', keepFile.toString());

      const response = await api.post<UploadResponse>('/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        // Add progress tracking if needed
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress?.(percentCompleted);
          }
        },
      });

      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  // New function to poll for analysis completion
  pollAnalysisStatus: async (
    analysisId: string,
    onProgress?: (progress: number) => void,
    interval: number = 5000, // Increased from 2000ms to 5000ms (5 seconds) to reduce backend load
    maxAttempts: number = 180 // Adjusted to maintain 15 minutes timeout (180 * 5 seconds)
  ): Promise<{ status: string; analysis?: any }> => {
    let attempts = 0;
    
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          attempts++;
          
          // Get analysis status
          const statusResponse = await documentAPI.getAnalysisStatus(analysisId);
          
          // Call progress callback if provided
          onProgress?.(statusResponse.progress_percentage);
          
          // Check if analysis is complete
          if (statusResponse.status === 'completed') {
            // Get the full analysis
            const analysisResponse = await documentAPI.getAnalysisById(analysisId);
            resolve({ status: 'completed', analysis: analysisResponse });
          } else if (statusResponse.status === 'failed') {
            reject(new Error('Analysis failed: ' + (statusResponse.message || 'Unknown error')));
          } else if (attempts >= maxAttempts) {
            reject(new Error('Analysis timeout: The analysis is taking longer than expected. Please try again with a simpler query or check back later.'));
          } else {
            // Continue polling
            setTimeout(poll, interval);
          }
        } catch (error) {
          reject(error);
        }
      };
      
      // Start polling
      poll();
    });
  },

  getAnalysisHistory: async (
    page: number = 1,
    pageSize: number = 10,
    status?: string
  ): Promise<{
    analyses: Analysis[];
    pagination: {
      page: number;
      page_size: number;
      total_count: number;
      has_more: boolean;
      total_pages: number;
    };
  }> => {
    try {
      const params: any = { page, page_size: pageSize };
      if (status) params.status = status;

      const response = await api.get('/analysis/history', { params });
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  getAnalysisById: async (analysisId: string): Promise<{ analysis: Analysis; document?: Document }> => {
    try {
      const response = await api.get(`/analysis/${analysisId}`);
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  getAnalysisStatus: async (analysisId: string): Promise<{
    status: string;
    message: string;
    analysis_id: string;
    progress_percentage: number;
  }> => {
    try {
      const response = await api.post(`/analysis/${analysisId}/status`);
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  deleteAnalysis: async (analysisId: string): Promise<{ message: string }> => {
    try {
      const response = await api.delete(`/analysis/${analysisId}`);
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  getDocuments: async (
    page: number = 1,
    pageSize: number = 10
  ): Promise<{
    documents: Document[];
    pagination: {
      page: number;
      page_size: number;
      total_count: number;
      has_more: boolean;
      total_pages: number;
    };
  }> => {
    try {
      const response = await api.get('/documents', {
        params: { page, page_size: pageSize },
      });
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  searchDocuments: async (
    searchTerm: string = '',
    page: number = 1,
    pageSize: number = 10
  ): Promise<{
    documents: Document[];
    pagination: {
      page: number;
      page_size: number;
      total_count: number;
      has_more: boolean;
      total_pages: number;
    };
    search_term: string;
  }> => {
    try {
      const response = await api.get('/documents/search', {
        params: { search_term: searchTerm, page, page_size: pageSize },
      });
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  deleteDocument: async (documentId: string): Promise<{ message: string }> => {
    try {
      const response = await api.delete(`/documents/${documentId}`);
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  getStatistics: async (): Promise<{
    user_statistics: any;
    system_statistics: any;
    database_info: any;
  }> => {
    try {
      const response = await api.get('/statistics');
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  // Export analysis report
  exportAnalysisReport: async (analysisId: string, format: string = 'html'): Promise<Blob> => {
    console.log('Attempting to export analysis:', analysisId, 'format:', format);
    try {
      const response = await api.get(`/analysis/${analysisId}/export`, {
        params: { format },
        responseType: 'blob'
      });
      return response.data;
    } catch (error: any) {
      console.error('Export analysis error:', error);
      // Check if it's an authentication error
      if (error.response?.status === 401) {
        // Clear local auth data and redirect to login
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
        window.location.href = '/login';
      }
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  // Download analysis report
  downloadAnalysisReport: async (analysisId: string, filename?: string, format: string = 'html'): Promise<void> => {
    try {
      const blob = await documentAPI.exportAnalysisReport(analysisId, format);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || `analysis-report-${analysisId}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      console.error('Download analysis error:', error);
      // Provide a more user-friendly error message
      let errorMessage = 'Failed to download report. Please try again later.';
      
      if (error?.response?.status === 401) {
        errorMessage = 'Authentication required. Please log in again.';
      } else if (error?.response?.status === 403) {
        errorMessage = 'Access denied. You do not have permission to download this report.';
      } else if (error?.response?.status === 404) {
        errorMessage = 'Report not found.';
      } else if (error?.response?.status === 500) {
        errorMessage = 'Server error. Please try again later.';
      } else if (error?.message) {
        errorMessage = error.message;
      }
      
      // If we have response data, try to parse it as JSON to get the detail message
      if (error?.response?.data) {
        try {
          // For blob responses, we need to read the blob as text first
          if (error.response.data instanceof Blob) {
            const text = await error.response.data.text();
            try {
              const errorObj = JSON.parse(text);
              if (errorObj.detail) {
                errorMessage = errorObj.detail;
              }
            } catch (parseError) {
              // If parsing fails, use the raw text if it's not empty
              if (text.trim()) {
                errorMessage = text.trim();
              }
            }
          }
        } catch (e) {
          console.error('Error parsing error response:', e);
        }
      }
      
      throw new Error(errorMessage);
    }
  },

  // Upload with progress tracking
  uploadAndAnalyzeWithProgress: async (
    file: File,
    query: string,
    keepFile: boolean = false,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> => {
    try {
      return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('query', query);
        formData.append('keep_file', keepFile.toString());

        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable && onProgress) {
            const progress = (event.loaded / event.total) * 100;
            onProgress(progress);
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status === 200) {
            try {
              const result = JSON.parse(xhr.responseText);
              resolve(result);
            } catch (parseError) {
              reject(new Error('Failed to parse response'));
            }
          } else {
            // Try to parse error response
            let errorMessage = `HTTP ${xhr.status}: ${xhr.statusText}`;
            try {
              const errorResponse = JSON.parse(xhr.responseText);
              errorMessage = errorResponse.detail || errorMessage;
            } catch (e) {
              // If we can't parse the error, use the status text
            }
            reject(new Error(errorMessage));
          }
        });

        xhr.addEventListener('error', () => {
          reject(new Error('Network error during upload'));
        });

        xhr.addEventListener('timeout', () => {
          reject(new Error('Upload timeout'));
        });

        // Configure request
        const token = localStorage.getItem('auth_token');
        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }

        xhr.timeout = 5 * 60 * 1000; // 5 minutes timeout
        xhr.open('POST', `${API_BASE_URL}/analyze`);
        xhr.send(formData);
      });
    } catch (error) {
      console.error('Upload and analyze error:', error);
      throw error;
    }
  }
};

// Performance API
export const performanceAPI = {
  getLLMMetrics: async (): Promise<any> => {
    try {
      const response = await api.get('/metrics/llm');
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  getAgentPerformance: async (): Promise<any> => {
    try {
      const response = await api.get('/performance/agents');
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  getToolPerformance: async (): Promise<any> => {
    try {
      const response = await api.get('/performance/tools');
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  getDashboardData: async (): Promise<any> => {
    try {
      const response = await api.get('/performance/dashboard');
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  }
};

// Health Check API
export const healthAPI = {
  checkHealth: async (): Promise<{
    status: string;
    services: Record<string, string>;
    database_info: any;
  }> => {
    try {
      // Use healthApi instance without custom headers to avoid CORS preflight issues
      const response = await healthApi.get('/health');
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },

  getSystemInfo: async (): Promise<{
    message: string;
    status: string;
    version: string;
    features: string[];
    database: any;
  }> => {
    try {
      // Use healthApi instance without custom headers to avoid CORS preflight issues
      const response = await healthApi.get('/');
      return response.data;
    } catch (error: any) {
      const message = extractErrorMessage(error);
      throw new Error(message);
    }
  },
};

// Storage Utility Functions
export const storage = {
  getToken: (): string | null => {
    return localStorage.getItem('auth_token');
  },

  getUser: (): User | null => {
    const userData = localStorage.getItem('user_data');
    return userData ? JSON.parse(userData) : null;
  },

  clearAuth: (): void => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
  },

  isAuthenticated: (): boolean => {
    return !!storage.getToken();
  },
};

export default api;

// Legacy healthCheck alias for backward compatibility
export const healthCheck = healthAPI.checkHealth;
