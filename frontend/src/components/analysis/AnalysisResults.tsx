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
      <div className="whitespace-pre-wrap text-gray-700 font-mono text-sm p-4 bg-gray-50 rounded-lg border">
        {analysis || 'No analysis result available'}
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onNewAnalysis}
          className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>New Analysis</span>
        </button>
        
        <div className="flex items-center space-x-4">
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
            ✓ Analysis Complete
          </span>
        </div>
      </div>

      {/* File Info Card */}
      <div className="card mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            <FileText className="w-12 h-12 text-blue-600" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-1">
                {result.file_info?.filename || 'Unknown Document'}
              </h2>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
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
          
          <button 
            className="btn-secondary flex items-center space-x-2" 
            onClick={handleDownloadReport}
            disabled={isDownloading}
          >
            <Download className="w-4 h-4" />
            <span>{isDownloading ? 'Downloading...' : 'Download Report'}</span>
          </button>
        </div>
        
        {/* Query */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Analysis Query:</h4>
          <p className="text-gray-700 bg-gray-50 p-3 rounded-lg">
            {result.query || 'No query provided'}
          </p>
        </div>
      </div>

      {/* Analysis Results */}
      <div className="card">
        <div className="border-b border-gray-200 pb-4 mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Financial Analysis</h2>
          <p className="text-gray-600 mt-1">AI-powered insights and recommendations</p>
        </div>
        
        <div className="prose prose-lg max-w-none">
          {formatAnalysis(result.result || '')}
        </div>
        
        {/* Metadata */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-900">Processing ID:</span>
              <p className="text-gray-600 font-mono">{result.metadata?.processing_id || result.analysis_id}</p>
            </div>
            <div>
              <span className="font-medium text-gray-900">File Type:</span>
              <p className="text-gray-600">{result.metadata?.file_type || 'PDF'}</p>
            </div>
            <div>
              <span className="font-medium text-gray-900">Processed:</span>
              <p className="text-gray-600">
                {result.metadata?.analysis_timestamp ? 
                  new Date(result.metadata.analysis_timestamp).toLocaleString() : 
                  'Unknown'
                }
              </p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Action Buttons */}
      <div className="flex justify-center space-x-4 mt-8">
        <button onClick={onNewAnalysis} className="btn-primary">
          Analyze Another Document
        </button>
        <button className="btn-secondary">
          Share Results
        </button>
      </div>
    </div>
  );
};

export default AnalysisResults;
