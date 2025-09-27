import React from 'react';
import { FileText, Download, ArrowLeft, Clock, Database } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface AnalysisResultsProps {
  result: AnalysisResponse;
  onNewAnalysis: () => void;
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ 
  result, 
  onNewAnalysis 
}) => {
  const formatAnalysis = (analysis: string) => {
    // Split by double newlines to create paragraphs
    const paragraphs = analysis.split('\n\n').filter(p => p.trim());
    
    return paragraphs.map((paragraph, index) => {
      // Check if it's a header (starts with ##, **, or is all caps)
      if (paragraph.startsWith('##')) {
        return (
          <h3 key={index} className="text-xl font-bold text-gray-900 mt-6 mb-3">
            {paragraph.replace(/^##\s*/, '')}
          </h3>
        );
      }
      
      if (paragraph.startsWith('**') && paragraph.endsWith('**')) {
        return (
          <h4 key={index} className="text-lg font-semibold text-gray-800 mt-4 mb-2">
            {paragraph.replace(/^\*\*/, '').replace(/\*\*$/, '')}
          </h4>
        );
      }
      
      // Check for bullet points
      if (paragraph.includes('- ')) {
        const items = paragraph.split('- ').filter(item => item.trim());
        return (
          <ul key={index} className="list-disc list-inside space-y-1 mb-4">
            {items.map((item, itemIndex) => (
              <li key={itemIndex} className="text-gray-700">
                {item.trim()}
              </li>
            ))}
          </ul>
        );
      }
      
      // Regular paragraph
      return (
        <p key={index} className="text-gray-700 mb-4 leading-relaxed">
          {paragraph}
        </p>
      );
    });
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
                {result.file_info.filename}
              </h2>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Database className="w-4 h-4" />
                  <span>{result.file_info.size_mb} MB</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>{result.metadata.file_type}</span>
                </div>
              </div>
            </div>
          </div>
          
          <button className="btn-secondary flex items-center space-x-2">
            <Download className="w-4 h-4" />
            <span>Download Report</span>
          </button>
        </div>
        
        {/* Query */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Analysis Query:</h4>
          <p className="text-gray-700 bg-gray-50 p-3 rounded-lg">
            {result.query}
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
          {formatAnalysis(result.analysis)}
        </div>
        
        {/* Metadata */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-900">Processing ID:</span>
              <p className="text-gray-600 font-mono">{result.metadata.processing_id}</p>
            </div>
            <div>
              <span className="font-medium text-gray-900">File Type:</span>
              <p className="text-gray-600">{result.metadata.file_type}</p>
            </div>
            <div>
              <span className="font-medium text-gray-900">Status:</span>
              <p className="text-gray-600">{result.metadata.analysis_timestamp}</p>
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
