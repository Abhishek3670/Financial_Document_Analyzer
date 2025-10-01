import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight, 
  Trash2,
  Download,
  Eye,
  Loader2
} from 'lucide-react';
import { useAuth } from './../auth/Auth';
import { documentAPI, Document } from '../../api';

interface DocumentsProps {
  onViewDocument?: (document: Document) => void;
}

// Utility functions
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatRelativeTime = (dateString: string): string => {
  if (!dateString) return 'Unknown time';
  
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'Invalid date';
  
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

const Documents: React.FC<DocumentsProps> = ({ onViewDocument }) => {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [isSearching, setIsSearching] = useState(false);

  const pageSize = 10;

  useEffect(() => {
    if (user) {
      loadDocuments(true);
    }
  }, [currentPage, user]);

  const loadDocuments = async (resetData: boolean = false) => {
    try {
      setLoading(true);
      setError('');

      const response = await documentAPI.getDocuments(
        currentPage,
        pageSize
      );

      setDocuments(response.documents);
      setTotalPages(response.pagination.total_pages);
      setTotalCount(response.pagination.total_count);
      
    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const searchDocuments = async () => {
    if (!searchTerm.trim()) {
      loadDocuments(true);
      return;
    }

    try {
      setIsSearching(true);
      setError('');

      const response = await documentAPI.searchDocuments(
        searchTerm,
        currentPage,
        pageSize
      );

      setDocuments(response.documents);
      setTotalPages(response.pagination.total_pages);
      setTotalCount(response.pagination.total_count);
      
    } catch (err: any) {
      setError(err.message || 'Failed to search documents');
    } finally {
      setIsSearching(false);
    }
  };

  const handleDeleteDocument = async (documentId: string, documentName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${documentName}"? This action cannot be undone.`)) return;

    try {
      await documentAPI.deleteDocument(documentId);
      
      // Refresh the list
      await loadDocuments(true);
    } catch (err: any) {
      console.error('Delete document error:', err);
      setError(err.message || 'Failed to delete document. Please try again.');
    }
  };

  const handleSearch = () => {
    setCurrentPage(1);
    searchDocuments();
  };

  const handleResetFilters = () => {
    setSearchTerm('');
    setCurrentPage(1);
    loadDocuments(true);
  };

  // Show login prompt if user is not authenticated
  if (!user) {
    return (
      <div className="text-center py-12">
        <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <FileText className="w-10 h-10 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Sign in to view your documents</h3>
        <p className="text-gray-500">Please sign in to access your uploaded documents.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Document Management</h2>
          <p className="text-gray-500 mt-1">{totalCount} total documents</p>
        </div>
        
        <button
          onClick={() => loadDocuments(true)}
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
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 w-full border border-gray-300 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>

          {/* Actions */}
          <div className="flex space-x-2">
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isSearching ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 inline animate-spin" />
                  Searching...
                </>
              ) : (
                'Search'
              )}
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
          <span className="ml-2 text-gray-600">Loading documents...</span>
        </div>
      ) : (
        <>
          {/* Document List */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            {documents.length === 0 ? (
              <div className="p-12 text-center">
                <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {searchTerm ? 'No documents found' : 'No documents uploaded'}
                </h3>
                <p className="text-gray-500">
                  {searchTerm 
                    ? 'Try adjusting your search terms.' 
                    : 'Upload documents through the analysis page to get started.'}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {documents.map((document) => (
                  <div key={document.id} className="p-6 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-start space-x-4">
                        <div className="flex-shrink-0">
                          <FileText className="w-10 h-10 text-blue-600" />
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-medium text-gray-900 truncate">
                            {document.original_filename}
                          </h3>
                          
                          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <span>
                              Size: {formatFileSize(document.file_size)}
                            </span>
                            
                            <span>
                              Uploaded: {formatRelativeTime(document.upload_timestamp)}
                            </span>
                            
                            <span>
                              Type: {document.file_type}
                            </span>
                            
                            {document.is_processed && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                Processed
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {onViewDocument && (
                          <button
                            onClick={() => onViewDocument(document)}
                            className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                          >
                            <Eye className="w-3 h-3 mr-1" />
                            View
                          </button>
                        )}
                        
                        <button
                          onClick={() => handleDeleteDocument(document.id, document.original_filename)}
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

export default Documents;