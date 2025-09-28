import React, { useState, useEffect } from 'react';
import { 
  Clock, 
  FileText, 
  Filter, 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  Eye,
  Trash2,
  Download,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { useAuth } from './Auth';
import { documentAPI, Analysis } from '../api';

interface AnalysisHistoryProps {
  onViewAnalysis: (analysis: Analysis) => void;
}

// Utility functions
const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  
  if (diffHours < 1) {
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    return `${diffMinutes} minutes ago`;
  } else if (diffHours < 24) {
    return `${Math.floor(diffHours)} hours ago`;
  } else {
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} days ago`;
  }
};

const formatProcessingTime = (startTime: string, endTime?: string): string => {
  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  const diffMs = end.getTime() - start.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  
  if (diffSeconds < 60) {
    return `${diffSeconds}s`;
  } else {
    const diffMinutes = Math.floor(diffSeconds / 60);
    return `${diffMinutes}m ${diffSeconds % 60}s`;
  }
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'completed': return 'text-green-600 bg-green-100';
    case 'processing': return 'text-yellow-600 bg-yellow-100';
    case 'failed': return 'text-red-600 bg-red-100';
    case 'pending': return 'text-gray-600 bg-gray-100';
    default: return 'text-gray-600 bg-gray-100';
  }
};

const AnalysisHistory: React.FC<AnalysisHistoryProps> = ({ onViewAnalysis }) => {
  const { user } = useAuth();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const pageSize = 10;

  useEffect(() => {
    if (user) {
      loadAnalyses(true);
    }
  }, [currentPage, statusFilter, user]);

  const loadAnalyses = async (resetData: boolean = false) => {
    try {
      setLoading(true);
      setError('');

      const response = await documentAPI.getAnalysisHistory(
        currentPage,
        pageSize,
        statusFilter || undefined
      );

      setAnalyses(response.analyses);
      setTotalPages(response.pagination.total_pages);
      setTotalCount(response.pagination.total_count);
      
    } catch (err: any) {
      setError(err.message || 'Failed to load analysis history');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAnalysis = async (analysisId: string) => {
    if (!window.confirm('Are you sure you want to delete this analysis? This action cannot be undone.')) return;

    try {
      await documentAPI.deleteAnalysis(analysisId);
      
      // Show success message
      // In a real application, you might want to use a toast notification here
      
      // Refresh the list
      await loadAnalyses(true);
    } catch (err: any) {
      console.error('Delete analysis error:', err);
      setError(err.message || 'Failed to delete analysis. Please try again.');
      
      // Show error message to user
      // In a real application, you might want to use a toast notification here
    }
  };

  const handleSearch = () => {
    setCurrentPage(1);
    loadAnalyses(true);
  };

  const handleResetFilters = () => {
    setSearchTerm('');
    setStatusFilter('');
    setCurrentPage(1);
    loadAnalyses(true);
  };

  const filteredAnalyses = analyses.filter(analysis => {
    if (searchTerm && !analysis.query?.toLowerCase()?.includes(searchTerm.toLowerCase()) &&
        !analysis.document?.original_filename?.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    return true;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-yellow-600 animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-600" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-gray-600" />;
    }
  };

  // Show login prompt if user is not authenticated
  if (!user) {
    return (
      <div className="text-center py-12">
        <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <FileText className="w-10 h-10 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Sign in to view your analysis history</h3>
        <p className="text-gray-500">Please sign in to access your previous document analyses.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Analysis History</h2>
          <p className="text-gray-500 mt-1">{totalCount} total analyses</p>
        </div>
        
        <button
          onClick={() => loadAnalyses(true)}
          disabled={loading}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
        >
          <Download className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search analyses..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 w-full border border-gray-300 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>

          {/* Status Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="pl-10 w-full border border-gray-300 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Status</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
            </select>
          </div>

          {/* Actions */}
          <div className="flex space-x-2">
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Search
            </button>
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-600">Loading analyses...</span>
        </div>
      ) : (
        <>
          {/* Analysis List */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {filteredAnalyses.length === 0 ? (
              <div className="p-12 text-center">
                <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No analyses found</h3>
                <p className="text-gray-500">Try adjusting your filters or upload a new document to get started.</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredAnalyses.map((analysis) => (
                  <div key={analysis.id} className="p-6 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-start space-x-4">
                        <div className="flex-shrink-0">
                          <FileText className="w-10 h-10 text-blue-600" />
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            {getStatusIcon(analysis.status)}
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(analysis.status)}`}>
                              {analysis.status.charAt(0).toUpperCase() + analysis.status.slice(1)}
                            </span>
                          </div>
                          
                          <h3 className="text-sm font-medium text-gray-900 truncate">
                            {analysis.document?.original_filename || 'Unknown Document'}
                          </h3>
                          
                          <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                            {analysis.query}
                          </p>
                          
                          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <span>
                              <Clock className="w-3 h-3 inline mr-1" />
                              {formatRelativeTime(analysis.created_at)}
                            </span>
                            
                            {analysis.completed_at && (
                              <span>
                                Processing: {formatProcessingTime(analysis.created_at, analysis.completed_at)}
                              </span>
                            )}
                            
                            {analysis.document && (
                              <span>
                                {(analysis.document.file_size / 1024 / 1024).toFixed(1)} MB
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {analysis.status === 'completed' && (
                          <button
                            onClick={() => onViewAnalysis(analysis)}
                            className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                          >
                            <Eye className="w-3 h-3 mr-1" />
                            View
                          </button>
                        )}
                        
                        <button
                          onClick={() => handleDeleteAnalysis(analysis.id)}
                          className="inline-flex items-center px-3 py-1.5 border border-red-300 shadow-sm text-xs font-medium rounded text-red-700 bg-white hover:bg-red-50"
                        >
                          <Trash2 className="w-3 h-3 mr-1" />
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} results
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Previous
                </button>
                
                <span className="text-sm text-gray-700">
                  Page {currentPage} of {totalPages}
                </span>
                
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AnalysisHistory;
