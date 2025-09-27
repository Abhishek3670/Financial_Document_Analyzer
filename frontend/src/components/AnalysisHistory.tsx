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
import { 
  AnalysisHistoryResponse, 
  AnalysisHistoryItem, 
  FilterState, 
  PaginationState 
} from '../types';
import { 
  getAnalysisHistory, 
  deleteAnalysis,
  formatRelativeTime, 
  formatProcessingTime,
  getStatusColor 
} from '../api';

interface AnalysisHistoryProps {
  onViewAnalysis: (analysis: AnalysisHistoryItem) => void;
}

const AnalysisHistory: React.FC<AnalysisHistoryProps> = ({ onViewAnalysis }) => {
  const [data, setData] = useState<AnalysisHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    pageSize: 10,
    totalCount: 0,
    hasMore: false
  });
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Load analysis history
  const loadHistory = async (page: number = 1, status?: string, resetData: boolean = false) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getAnalysisHistory(page, pagination.pageSize, status);
      
      if (resetData) {
        setData(response);
      } else {
        setData(prevData => ({
          ...response,
          analyses: prevData ? [...prevData.analyses, ...response.analyses] : response.analyses
        }));
      }

      setPagination({
        page: response.pagination.page,
        pageSize: response.pagination.page_size,
        totalCount: response.pagination.total_count,
        hasMore: response.pagination.has_more
      });

    } catch (err: any) {
      console.error('Error loading analysis history:', err);
      setError('Failed to load analysis history');
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadHistory(1, filters.status, true);
  }, [filters.status]);

  // Handle status filter change
  const handleStatusFilter = (status: string | undefined) => {
    setFilters(prev => ({ ...prev, status }));
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  // Handle search
  const handleSearch = (term: string) => {
    setSearchTerm(term);
    // For now, we'll do client-side filtering
    // In a real app, you'd send the search term to the API
  };

  // Load more results
  const loadMore = () => {
    if (!loading && pagination.hasMore) {
      loadHistory(pagination.page + 1, filters.status, false);
    }
  };

  // Handle delete
  const handleDelete = async (analysisId: string) => {
    if (!window.confirm('Are you sure you want to delete this analysis? This action cannot be undone.')) {
      return;
    }

    setDeletingId(analysisId);
    
    try {
      await deleteAnalysis(analysisId);
      
      // Remove from local state
      setData(prevData => {
        if (!prevData) return null;
        return {
          ...prevData,
          analyses: prevData.analyses.filter(a => a.id !== analysisId),
          pagination: {
            ...prevData.pagination,
            total_count: prevData.pagination.total_count - 1
          }
        };
      });

      setPagination(prev => ({ 
        ...prev, 
        totalCount: prev.totalCount - 1 
      }));

    } catch (err: any) {
      console.error('Error deleting analysis:', err);
      alert('Failed to delete analysis. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  // Filter analyses based on search term
  const filteredAnalyses = data?.analyses?.filter(analysis =>
    analysis.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
    analysis.document?.original_filename?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-600" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <AlertTriangle className="w-5 h-5 text-gray-600" />;
    }
  };

  if (error && !data) {
    return (
      <div className="text-center py-12">
        <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading History</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={() => loadHistory(1, filters.status, true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Analysis History</h2>
          <p className="text-gray-600">
            {pagination.totalCount} total analyses
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border p-4 space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search by query or filename..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={filters.status || ''}
              onChange={(e) => handleStatusFilter(e.target.value || undefined)}
              className="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Status</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Analysis List */}
      {loading && !data && (
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">Loading analysis history...</p>
        </div>
      )}

      {filteredAnalyses.length === 0 && !loading ? (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Analyses Found</h3>
          <p className="text-gray-600">
            {searchTerm || filters.status
              ? 'Try adjusting your filters or search term'
              : 'Upload a document to create your first analysis'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredAnalyses.map((analysis) => (
            <div
              key={analysis.id}
              className="bg-white rounded-lg border hover:shadow-md transition-shadow"
            >
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* Status and Timestamp */}
                    <div className="flex items-center space-x-3 mb-3">
                      {getStatusIcon(analysis.status)}
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(analysis.status)}`}>
                        {analysis.status}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatRelativeTime(analysis.started_at)}
                      </span>
                      {analysis.processing_time_seconds && (
                        <span className="text-sm text-gray-500">
                          • {formatProcessingTime(analysis.processing_time_seconds)}
                        </span>
                      )}
                    </div>

                    {/* Document Info */}
                    {analysis.document && (
                      <div className="flex items-center space-x-2 mb-3">
                        <FileText className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-700 font-medium">
                          {analysis.document.original_filename}
                        </span>
                        <span className="text-xs text-gray-500">
                          ({(analysis.document.file_size / 1024 / 1024).toFixed(2)} MB)
                        </span>
                      </div>
                    )}

                    {/* Query */}
                    <p className="text-gray-900 mb-3">
                      <span className="font-medium">Query: </span>
                      {analysis.query}
                    </p>

                    {/* Result Preview (for completed analyses) */}
                    {analysis.status === 'completed' && analysis.result && (
                      <div className="bg-gray-50 rounded-lg p-3 mb-3">
                        <p className="text-sm text-gray-700 line-clamp-2">
                          {analysis.result.substring(0, 200)}
                          {analysis.result.length > 200 && '...'}
                        </p>
                      </div>
                    )}

                    {/* Error Message (for failed analyses) */}
                    {analysis.status === 'failed' && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                        <p className="text-sm text-red-700">
                          Analysis failed. Please try again.
                        </p>
                      </div>
                    )}

                    {/* Metadata */}
                    <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                      {analysis.confidence_score && (
                        <span>Confidence: {(analysis.confidence_score * 100).toFixed(1)}%</span>
                      )}
                      {analysis.key_insights_count && (
                        <span>Insights: {analysis.key_insights_count}</span>
                      )}
                      <span>Type: {analysis.analysis_type}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 ml-4">
                    {analysis.status === 'completed' && (
                      <>
                        <button
                          onClick={() => onViewAnalysis(analysis)}
                          className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="View Analysis"
                        >
                          <Eye className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => {/* TODO: Implement export */}}
                          className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                          title="Export Analysis"
                        >
                          <Download className="w-5 h-5" />
                        </button>
                      </>
                    )}
                    
                    <button
                      onClick={() => handleDelete(analysis.id)}
                      disabled={deletingId === analysis.id}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                      title="Delete Analysis"
                    >
                      {deletingId === analysis.id ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Trash2 className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Load More Button */}
          {pagination.hasMore && (
            <div className="text-center py-6">
              <button
                onClick={loadMore}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium transition-colors flex items-center space-x-2 mx-auto"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Loading...</span>
                  </>
                ) : (
                  <>
                    <span>Load More</span>
                    <ChevronRight className="w-5 h-5" />
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalysisHistory;
