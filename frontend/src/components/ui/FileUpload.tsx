import React, { useState, useRef } from 'react';
import { Upload, FileText, X, Loader2, AlertCircle, Save } from 'lucide-react';
import type { AnalysisResponse } from '../../types';
import { documentAPI } from '../../api';

// Define interface for upload form state
interface UploadFormState {
  selectedFile: File | null;
  query: string;
  keepFile: boolean;
  error: string | null;
}

interface FileUploadProps {
  onAnalysisComplete: (result: AnalysisResponse) => void;
  className?: string;
  // Added props for lifted state
  uploadFormState: UploadFormState;
  onFormStateChange: (state: UploadFormState) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ 
  onAnalysisComplete, 
  className = '',
  uploadFormState,
  onFormStateChange
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { selectedFile, query, keepFile, error } = uploadFormState;

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onFormStateChange({ ...uploadFormState, selectedFile: file, error: null });
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      onFormStateChange({ ...uploadFormState, selectedFile: file, error: null });
    }
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    onFormStateChange({ ...uploadFormState, error: null });
    setProgress(0);

    try {
      // Upload file and start analysis
      const uploadResult = await documentAPI.uploadAndAnalyze(
        selectedFile,
        query,
        keepFile,
        (progress) => setProgress(progress)
      );

      // If analysis is already complete (for backward compatibility)
      if (uploadResult.status === 'success' && uploadResult.analysis) {
        // Convert the upload response to the expected AnalysisResponse format
        const analysisResponse: AnalysisResponse = {
          id: uploadResult.analysis_id,
          status: uploadResult.status,
          result: uploadResult.analysis,
          analysis: uploadResult.analysis,
          query: uploadResult.query,
          created_at: uploadResult.metadata.analysis_timestamp,
          file_info: uploadResult.file_info,
          metadata: uploadResult.metadata
        };

        onAnalysisComplete(analysisResponse);
      } else if (uploadResult.status === 'processing' && uploadResult.analysis_id) {
        // Analysis is processing, start polling for completion
        try {
          const pollResult = await documentAPI.pollAnalysisStatus(
            uploadResult.analysis_id,
            (progress) => setProgress(progress)
          );
          
          if (pollResult.status === 'completed' && pollResult.analysis) {
            // Convert the analysis response to the expected AnalysisResponse format
            const analysisData = pollResult.analysis.analysis;
            const documentData = pollResult.analysis.document;
            
            const analysisResponse: AnalysisResponse = {
              id: analysisData.id,
              status: 'success',
              result: analysisData.result || '',
              analysis: analysisData.result || '',
              query: analysisData.query || '',
              created_at: analysisData.created_at,
              completed_at: analysisData.completed_at,
              file_info: {
                filename: documentData?.original_filename || 'Unknown',
                size_mb: documentData ? 
                  Math.round((documentData.file_size / 1024 / 1024) * 100) / 100 : 0,
                processed_at: analysisData.completed_at || analysisData.created_at
              },
              metadata: {
                processing_id: analysisData.id,
                file_type: 'PDF',
                analysis_timestamp: analysisData.completed_at || analysisData.created_at,
                kept_file: false
              }
            };

            onAnalysisComplete(analysisResponse);
          }
        } catch (pollError: any) {
          throw new Error(`Analysis failed: ${pollError.message || 'Unknown error'}`);
        }
      } else {
        throw new Error('Unexpected response from server');
      }
      
      // Reset form
      onFormStateChange({ 
        selectedFile: null, 
        query: 'Provide a comprehensive financial analysis of this document',
        keepFile: false,
        error: null
      });
      setProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      let errorMessage = err.message || 'Analysis failed';
      
      // Make error messages more user-friendly
      if (errorMessage.includes('insufficient_quota') || errorMessage.includes('429')) {
        errorMessage = 'OpenAI API quota exceeded. Please check your OpenAI plan and billing details. For more information, visit https://platform.openai.com/docs/guides/error-codes/api-errors';
      } else if (errorMessage.toLowerCase().includes('rate limit')) {
        errorMessage = 'API rate limit exceeded. Please try again later.';
      } else if (errorMessage.toLowerCase().includes('timeout')) {
        errorMessage = 'Request timed out. Please try again with a simpler query or check your network connection.';
      } else if (errorMessage.toLowerCase().includes('authentication') || errorMessage.toLowerCase().includes('unauthorized')) {
        errorMessage = 'Authentication failed. Please check your API credentials.';
      } else if (errorMessage.toLowerCase().includes('permission') || errorMessage.toLowerCase().includes('forbidden')) {
        errorMessage = 'Access forbidden. Please check your permissions.';
      } else if (errorMessage.toLowerCase().includes('not found')) {
        errorMessage = 'Resource not found. The requested resource may have been deleted.';
      } else if (errorMessage.toLowerCase().includes('network') || errorMessage.toLowerCase().includes('connection')) {
        errorMessage = 'Network error. Please check your internet connection and try again.';
      }
      
      onFormStateChange({ ...uploadFormState, error: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveFile = () => {
    onFormStateChange({ ...uploadFormState, selectedFile: null });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleQueryChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onFormStateChange({ ...uploadFormState, query: e.target.value });
  };

  const handleKeepFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFormStateChange({ ...uploadFormState, keepFile: e.target.checked });
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
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors dark:border-gray-600 dark:hover:border-blue-400 dark:bg-gray-800"
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="space-y-4">
          <div className="mx-auto w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center dark:bg-blue-900/30">
            <Upload className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Upload Document</h3>
            <p className="text-gray-500 dark:text-gray-400">Drag and drop or click to select a PDF file</p>
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
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 cursor-pointer dark:bg-blue-600 dark:hover:bg-blue-700"
          >
            Choose File
          </label>
        </div>
      </div>

      {/* Selected File Display */}
      {selectedFile && (
        <div className="bg-gray-50 rounded-lg p-4 dark:bg-gray-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">{selectedFile.name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <button
              onClick={handleRemoveFile}
              className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Analysis Query */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
          Analysis Query (Optional)
        </label>
        <textarea
          value={query}
          onChange={handleQueryChange}
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
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
            onChange={handleKeepFileChange}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600"
          />
          <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Keep file for future reference</span>
        </label>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 dark:bg-red-900/20 dark:border-red-800">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Analysis Error</h3>
              <p className="text-sm text-red-700 mt-1 dark:text-red-300">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Progress Bar */}
      {isLoading && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
            <span>Processing document...</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300 dark:bg-blue-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Analyze Button */}
      <button
        onClick={handleAnalyze}
        disabled={!selectedFile || isLoading}
        className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed dark:bg-blue-600 dark:hover:bg-blue-700 dark:disabled:bg-gray-700"
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