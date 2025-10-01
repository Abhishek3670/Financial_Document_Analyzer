import React, { useState } from 'react';
import { FileText, Download, ArrowLeft, Clock, Database, AlertCircle } from 'lucide-react';
import type { AnalysisResponse } from '../../types';
import { documentAPI } from '../../api';

interface AnalysisResultsProps {
  result: AnalysisResponse;
  onNewAnalysis: () => void;
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ 
  result, 
  onNewAnalysis 
}) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadReport = async () => {
    if (!result.id) return;
    
    setIsDownloading(true);
    try {
      console.log('Analysis result for download:', result);
      console.log('Analysis ID:', result.id);
      const filename = `analysis-report-${result.id}.html`;
      await documentAPI.downloadAnalysisReport(result.id, filename, 'html');
    } catch (error: any) {
      console.error('Failed to download report:', error);
      
      // Handle different types of errors
      let errorMessage = 'Unknown error occurred';
      
      if (error?.response) {
        // Server responded with error status
        if (error.response.status === 401) {
          errorMessage = 'Authentication required. Please log in and try again.';
        } else if (error.response.status === 403) {
          errorMessage = 'Access denied. You do not have permission to download this report.';
        } else if (error.response.status === 404) {
          errorMessage = 'Report not found. The analysis may have been deleted.';
        } else if (error.response.status === 500) {
          errorMessage = 'Server error. Please try again later.';
        } else {
          errorMessage = error.response.data?.detail || error.response.statusText || 'Server error';
        }
      } else if (error?.request) {
        // Request was made but no response received
        errorMessage = 'Network error. Please check your connection and try again.';
      } else {
        // Something else happened
        errorMessage = error?.message || 'Failed to download report';
      }
      
      alert(`Failed to download report: ${errorMessage}. Please try again.`);
    } finally {
      setIsDownloading(false);
    }
  };

  const formatAnalysis = (analysis: string) => {
    // Display raw analysis result without any formatting
    return (
      <div className="whitespace-pre-wrap text-gray-700 font-mono text-sm p-4 bg-gray-50 rounded-lg border dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200">
        {analysis || 'No analysis result available'}
      </div>
    );
  };

  // Check if the analysis has an error message
  const hasError = result.status === 'failed' || (result as any).error_message;
  const errorMessage = hasError ? (result as any).error_message || 'Analysis failed' : '';

  // Function to determine if error is quota-related
  const isQuotaError = (error: string) => {
    return error.includes('insufficient_quota') || error.includes('429') || error.includes('quota');
  };

  // Function to determine error type and provide appropriate message
  const getErrorMessage = (error: string) => {
    if (isQuotaError(error)) {
      return {
        title: 'API Quota Exceeded',
        message: error,
        suggestion: 'Please check your API plan and billing details.',
        link: 'https://platform.openai.com/docs/guides/error-codes/api-errors'
      };
    } else if (error.toLowerCase().includes('rate limit')) {
      return {
        title: 'Rate Limit Exceeded',
        message: error,
        suggestion: 'Please try again later.',
        link: null
      };
    } else if (error.toLowerCase().includes('timeout')) {
      return {
        title: 'Request Timeout',
        message: error,
        suggestion: 'Please try again with a simpler query or check your network connection.',
        link: null
      };
    } else if (error.toLowerCase().includes('authentication') || error.toLowerCase().includes('unauthorized')) {
      return {
        title: 'Authentication Failed',
        message: error,
        suggestion: 'Please check your API credentials.',
        link: null
      };
    } else if (error.toLowerCase().includes('permission') || error.toLowerCase().includes('forbidden')) {
      return {
        title: 'Access Forbidden',
        message: error,
        suggestion: 'Please check your permissions.',
        link: null
      };
    } else if (error.toLowerCase().includes('not found')) {
      return {
        title: 'Resource Not Found',
        message: error,
        suggestion: 'The requested resource may have been deleted.',
        link: null
      };
    } else if (error.toLowerCase().includes('network') || error.toLowerCase().includes('connection')) {
      return {
        title: 'Network Error',
        message: error,
        suggestion: 'Please check your internet connection and try again.',
        link: null
      };
    } else {
      return {
        title: 'Analysis Failed',
        message: error,
        suggestion: 'Please try again or contact support if the issue persists.',
        link: null
      };
    }
  };

  const errorInfo = getErrorMessage(errorMessage);

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onNewAnalysis}
          className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 transition-colors dark:text-blue-400 dark:hover:text-blue-300"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>New Analysis</span>
        </button>
        
        <div className="flex items-center space-x-4">
          {hasError ? (
            <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium dark:bg-red-900/30 dark:text-red-200">
              ✗ Analysis Failed
            </span>
          ) : (
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium dark:bg-green-900/30 dark:text-green-200">
              ✓ Analysis Complete
            </span>
          )}
        </div>
      </div>

      {/* Error Message */}
      {hasError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg dark:bg-red-900/20 dark:border-red-800">
          <div className="flex items-start">
            <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0 dark:text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">{errorInfo.title}</h3>
              <div className="mt-1 text-sm text-red-700 dark:text-red-300">
                <p>{errorInfo.message}</p>
                {errorInfo.suggestion && <p className="mt-2">{errorInfo.suggestion}</p>}
                {errorInfo.link && (
                  <p className="mt-2">
                    <strong>For more information, visit{' '}
                    <a 
                      href={errorInfo.link} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="underline text-red-800 hover:text-red-900 dark:text-red-300 dark:hover:text-red-200"
                    >
                      OpenAI Error Codes Documentation
                    </a>
                    .</strong>
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* File Info Card */}
      <div className="card mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            <FileText className="w-12 h-12 text-blue-600 dark:text-blue-400" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-1 dark:text-white">
                {result.file_info?.filename || 'Unknown Document'}
              </h2>
              <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex items-center space-x-1">
                  <Database className="w-4 h-4" />
                  <span>{result.file_info?.size_mb || 0} MB</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>{result.metadata?.file_type || 'PDF'}</span>
                </div>
              </div>
            </div>
          </div>
          
          {!hasError && (
            <button 
              className="btn-secondary flex items-center space-x-2" 
              onClick={handleDownloadReport}
              disabled={isDownloading}
            >
              <Download className="w-4 h-4" />
              <span>{isDownloading ? 'Downloading...' : 'Download Report'}</span>
            </button>
          )}
        </div>
        
        {/* Query */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-900 mb-2 dark:text-white">Analysis Query:</h4>
          <p className="text-gray-700 bg-gray-50 p-3 rounded-lg dark:bg-gray-700 dark:text-gray-200">
            {result.query || 'No query provided'}
          </p>
        </div>
      </div>

      {/* Analysis Results */}
      {!hasError && (
        <div className="card">
          <div className="border-b border-gray-200 pb-4 mb-6 dark:border-gray-700">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Financial Analysis</h2>
            <p className="text-gray-600 mt-1 dark:text-gray-400">AI-powered insights and recommendations</p>
          </div>
          
          <div className="prose prose-lg max-w-none">
            {formatAnalysis(result.result || '')}
          </div>
          
          {/* Metadata */}
          <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-900 dark:text-white">Processing ID:</span>
                <p className="text-gray-600 font-mono dark:text-gray-400">{result.metadata?.processing_id || result.analysis_id}</p>
              </div>
              <div>
                <span className="font-medium text-gray-900 dark:text-white">File Type:</span>
                <p className="text-gray-600 dark:text-gray-400">{result.metadata?.file_type || 'PDF'}</p>
              </div>
              <div>
                <span className="font-medium text-gray-900 dark:text-white">Processed:</span>
                <p className="text-gray-600 dark:text-gray-400">
                  {result.metadata?.analysis_timestamp ? 
                    new Date(result.metadata.analysis_timestamp).toLocaleString() : 
                    'Unknown'
                  }
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Action Buttons */}
      <div className="flex justify-center space-x-4 mt-8">
        <button onClick={onNewAnalysis} className="btn-primary">
          {hasError ? 'Try Again' : 'Analyze Another Document'}
        </button>
        {!hasError && (
          <button className="btn-secondary">
            Share Results
          </button>
        )}
      </div>
    </div>
  );
};

export default AnalysisResults;
