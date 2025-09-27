import React, { useState, useRef } from 'react';
import { Upload, FileText, X, Loader2, AlertCircle, Save } from 'lucide-react';
import type { AnalysisResponse } from '../types';
import { documentAPI } from '../api';

interface FileUploadProps {
  onAnalysisComplete: (result: AnalysisResponse) => void;
  className?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({ onAnalysisComplete, className = '' }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('Provide a comprehensive financial analysis of this document');
  const [keepFile, setKeepFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    setError(null);
    setProgress(0);

    try {
      const result = await documentAPI.uploadAndAnalyze(
        selectedFile,
        query,
        keepFile,
        (progress) => setProgress(progress)
      );

      // Convert the upload response to the expected AnalysisResponse format
      const analysisResponse: AnalysisResponse = {
        id: result.analysis_id,
        status: result.status,
        result: result.analysis,
        analysis: result.analysis,
        query: result.query,
        created_at: result.metadata.analysis_timestamp,
        file_info: result.file_info,
        metadata: result.metadata
      };

      onAnalysisComplete(analysisResponse);
      
      // Reset form
      setSelectedFile(null);
      setProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      setError(err.message || 'Analysis failed');
    } finally {
      setIsLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* File Upload Area */}
      <div 
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors"
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="space-y-4">
          <div className="mx-auto w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center">
            <Upload className="w-6 h-6 text-blue-600" />
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900">Upload Document</h3>
            <p className="text-gray-500">Drag and drop or click to select a PDF file</p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
            id="file-input"
          />
          <label
            htmlFor="file-input"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 cursor-pointer"
          >
            Choose File
          </label>
        </div>
      </div>

      {/* Selected File Display */}
      {selectedFile && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="w-8 h-8 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-xs text-gray-500">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedFile(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Analysis Query */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Analysis Query (Optional)
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={3}
          placeholder="Describe what specific analysis you'd like..."
        />
      </div>

      {/* Options */}
      <div>
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={keepFile}
            onChange={(e) => setKeepFile(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="ml-2 text-sm text-gray-700">Keep file for future reference</span>
        </label>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Analysis Error</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Progress Bar */}
      {isLoading && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>Processing document...</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Analyze Button */}
      <button
        onClick={handleAnalyze}
        disabled={!selectedFile || isLoading}
        className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Analyzing...
          </>
        ) : (
          <>
            <Save className="w-4 h-4 mr-2" />
            Analyze Document
          </>
        )}
      </button>
    </div>
  );
};

export default FileUpload;
