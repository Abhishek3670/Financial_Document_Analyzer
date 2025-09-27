import axios, { AxiosResponse } from 'axios';
import {
  AnalysisResponse,
  AnalysisHistoryResponse,
  DocumentListResponse,
  StatisticsResponse,
  AnalysisStatusResponse,
  StorageStatistics,
  AnalyzeRequest,
  AnalysisHistoryItem
} from './types';

// Base configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// API functions

/**
 * Health check endpoint
 */
export const healthCheck = async (): Promise<any> => {
  const response = await api.get('/health');
  return response.data;
};

/**
 * Analyze a document
 */
export const analyzeDocument = async (
  request: AnalyzeRequest,
  onProgress?: (progress: number) => void
): Promise<AnalysisResponse> => {
  const formData = new FormData();
  formData.append('file', request.file);
  formData.append('query', request.query);
  if (request.keep_file !== undefined) {
    formData.append('keep_file', request.keep_file.toString());
  }

  const response = await api.post<AnalysisResponse>('/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
};

/**
 * Get analysis history with pagination and filtering
 */
export const getAnalysisHistory = async (
  page: number = 1,
  pageSize: number = 10,
  status?: string
): Promise<AnalysisHistoryResponse> => {
  const params: any = {
    page,
    page_size: pageSize,
  };

  if (status) {
    params.status = status;
  }

  const response = await api.get<AnalysisHistoryResponse>('/analysis/history', {
    params,
  });

  return response.data;
};

/**
 * Get a specific analysis by ID
 */
export const getAnalysisById = async (analysisId: string): Promise<{
  analysis: AnalysisHistoryItem;
  document: any;
}> => {
  const response = await api.get(`/analysis/${analysisId}`);
  return response.data;
};

/**
 * Delete an analysis
 */
export const deleteAnalysis = async (analysisId: string): Promise<{
  message: string;
  analysis_id: string;
}> => {
  const response = await api.delete(`/analysis/${analysisId}`);
  return response.data;
};

/**
 * Get user documents
 */
export const getDocuments = async (
  page: number = 1,
  pageSize: number = 10
): Promise<DocumentListResponse> => {
  const response = await api.get<DocumentListResponse>('/documents', {
    params: {
      page,
      page_size: pageSize,
    },
  });

  return response.data;
};

/**
 * Get user and system statistics
 */
export const getStatistics = async (): Promise<StatisticsResponse> => {
  const response = await api.get<StatisticsResponse>('/statistics');
  return response.data;
};

/**
 * Get analysis status (for polling)
 */
export const getAnalysisStatus = async (analysisId: string): Promise<AnalysisStatusResponse> => {
  const response = await api.post<AnalysisStatusResponse>(`/analysis/${analysisId}/status`);
  return response.data;
};

/**
 * Admin: Get storage statistics
 */
export const getStorageStatistics = async (): Promise<StorageStatistics> => {
  const response = await api.get<StorageStatistics>('/admin/storage-stats');
  return response.data;
};

/**
 * Admin: Run maintenance
 */
export const runMaintenance = async (): Promise<{
  status: string;
  maintenance_results: any;
  timestamp: string;
}> => {
  const response = await api.post('/admin/maintenance');
  return response.data;
};

// Utility functions

/**
 * Poll analysis status until completion
 */
export const pollAnalysisStatus = async (
  analysisId: string,
  onStatusUpdate?: (status: AnalysisStatusResponse) => void,
  maxAttempts: number = 60,
  intervalMs: number = 2000
): Promise<AnalysisStatusResponse> => {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const poll = async () => {
      try {
        attempts++;
        const status = await getAnalysisStatus(analysisId);
        
        if (onStatusUpdate) {
          onStatusUpdate(status);
        }

        if (status.status === 'completed' || status.status === 'failed') {
          resolve(status);
          return;
        }

        if (attempts >= maxAttempts) {
          reject(new Error('Polling timeout: Analysis took too long to complete'));
          return;
        }

        setTimeout(poll, intervalMs);
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
};

/**
 * Format file size in human-readable format
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Format processing time
 */
export const formatProcessingTime = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  }
};

/**
 * Format timestamp to relative time
 */
export const formatRelativeTime = (timestamp: string): string => {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMinutes < 1) {
    return 'just now';
  } else if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  } else if (diffDays < 30) {
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  } else {
    return date.toLocaleDateString();
  }
};

/**
 * Get status badge color
 */
export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800';
    case 'processing':
      return 'bg-blue-100 text-blue-800';
    case 'pending':
      return 'bg-yellow-100 text-yellow-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

export default api;

// Authentication API
export const authAPI = {
  register: async (userData: {
    email: string;
    username: string;
    password: string;
    first_name: string;
    last_name: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw { response: { data: error } };
    }

    return response.json();
  },

  login: async (credentials: { email: string; password: string }) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json();
      throw { response: { data: error } };
    }

    return response.json();
  },

  getProfile: async (token: string) => {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw { response: { data: error } };
    }

    return response.json();
  },

  logout: async (token: string) => {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    return response.ok;
  },

  changePassword: async (token: string, data: {
    current_password: string;
    new_password: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw { response: { data: error } };
    }

    return response.json();
  },

  updateProfile: async (token: string, data: {
    first_name?: string;
    last_name?: string;
    email?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/auth/profile`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw { response: { data: error } };
    }

    return response.json();
  }
};

// Update existing API functions to include auth header when token is available
const getAuthHeader = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// You can now update your existing API calls to include authentication
// For example, modify the analyzeDocument function to include auth headers:
/*
export const analyzeDocument = async (file: File, query: string) => {
  const formData = new FormData();
  formData.append('document', file);
  formData.append('query', query);

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: {
      ...getAuthHeader(), // Include auth header
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Analysis failed');
  }

  return response.json();
};
*/
