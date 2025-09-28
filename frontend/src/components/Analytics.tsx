import React, { useState, useEffect } from 'react';
import * as api from '../api';
import { Analysis } from '../api'; // Import the Analysis type

// Utility functions for date formatting
const formatRelativeTime = (dateString: string): string => {
  // Handle null or undefined dateString
  if (!dateString) {
    return 'Unknown time';
  }
  
  const date = new Date(dateString);
  
  // Check if date is valid
  if (isNaN(date.getTime())) {
    return 'Invalid date';
  }
  
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

const Analytics: React.FC = () => {
  const [analyses, setAnalyses] = useState<api.Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalyses = async () => {
      try {
        setLoading(true);
        const response = await api.documentAPI.getAnalysisHistory(1, 100); // Get recent analyses
        setAnalyses(response.analyses);
      } catch (err) {
        setError('Failed to load analysis history');
        console.error('Analytics error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalyses();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  // Filter for completed analyses
  const completedAnalyses = analyses.filter(analysis => analysis.status === 'completed');

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">CrewAI Analysis Results</h1>
        <p className="text-gray-600">View results from your financial document analyses</p>
      </div>

      {completedAnalyses.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border p-8 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No analyses yet</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by uploading a financial document for analysis.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {completedAnalyses.map((analysis) => (
            <div key={analysis.id} className="bg-white rounded-lg shadow-sm border overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">
                    {analysis.document?.original_filename || analysis.original_filename || 'Untitled Document'}
                  </h3>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    Completed
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  Analyzed {formatRelativeTime(analysis.completed_at || analysis.created_at)}
                </p>
              </div>
              <div className="px-6 py-4">
                <div className="mb-4">
                  <h4 className="text-md font-medium text-gray-900 mb-2">Analysis Query</h4>
                  <p className="text-gray-700">{analysis.query || 'No query provided'}</p>
                </div>
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-2">Document Info</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-sm text-gray-500">Analysis ID</p>
                      <p className="font-medium font-mono text-sm">{analysis.id.substring(0, 8)}...</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-sm text-gray-500">Status</p>
                      <p className="font-medium capitalize">{analysis.status}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-sm text-gray-500">Created</p>
                      <p className="font-medium">{analysis.created_at ? new Date(analysis.created_at).toLocaleDateString() : 'Unknown'}</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                <button
                  onClick={() => {
                    // In a real implementation, this would navigate to the detailed view
                    alert('In a complete implementation, this would show the full analysis result');
                  }}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  View Full Analysis
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Analytics;