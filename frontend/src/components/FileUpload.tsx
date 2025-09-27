import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Loader2, AlertCircle, Save } from 'lucide-react';
import { AnalysisResponse } from '../types';
import { analyzeDocument } from '../api';

interface FileUploadProps {
  onAnalysisComplete: (result: AnalysisResponse) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ 
  onAnalysisComplete, 
  isLoading, 
  setIsLoading 
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [query, setQuery] = useState('Provide a comprehensive financial analysis of this document');
  const [keepFile, setKeepFile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        setError('Please upload a PDF file only');
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        setError('File size must be less than 50MB');
        return;
      }
      setSelectedFile(file);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxFiles: 1,
    disabled: isLoading
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedFile) {
      setError('Please select a PDF file');
      return;
    }

    setIsLoading(true);
    setError(null);
    setProgress(0);

    try {
      const result = await analyzeDocument(
        {
          file: selectedFile,
          query,
          keep_file: keepFile
        },
        (progress) => {
          setProgress(progress);
        }
      );

      onAnalysisComplete(result);
      
      // Reset form on success
      setSelectedFile(null);
      setQuery('Provide a comprehensive financial analysis of this document');
      setKeepFile(false);
      
    } catch (err: any) {
      console.error('Analysis error:', err);
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          setError(err.response.data.detail);
        } else {
          setError(err.response.data.detail.error || 'Analysis failed');
        }
      } else if (err.message) {
        setError(err.message);
      } else {
        setError('Failed to analyze document. Please try again.');
      }
    } finally {
      setIsLoading(false);
      setProgress(0);
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    setError(null);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6 max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Upload Area */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Upload Financial Document
          </label>
          
          {!selectedFile ? (
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${isDragActive 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                }
                ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <input {...getInputProps()} />
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-lg font-medium text-gray-700 mb-2">
                {isDragActive ? 'Drop your PDF here' : 'Drag & drop your PDF here'}
              </p>
              <p className="text-sm text-gray-500">
                or click to browse (max 50MB)
              </p>
            </div>
          ) : (
            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <FileText className="w-8 h-8 text-blue-600" />
                  <div>
                    <p className="font-medium text-gray-900">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                {!isLoading && (
                  <button
                    type="button"
                    onClick={removeFile}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Query Input */}
        <div>
          <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
            Analysis Query
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
            rows={3}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            placeholder="What would you like to know about this financial document?"
          />
        </div>

        {/* Keep File Option */}
        <div className="flex items-center space-x-2">
          <input
            id="keepFile"
            type="checkbox"
            checked={keepFile}
            onChange={(e) => setKeepFile(e.target.checked)}
            disabled={isLoading}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
          />
          <label htmlFor="keepFile" className="flex items-center text-sm font-medium text-gray-700 cursor-pointer">
            <Save className="w-4 h-4 mr-1" />
            Keep file after analysis (for future reference)
          </label>
        </div>

        {/* Error Message */}
        {error && (
          <div className="flex items-center space-x-2 text-red-600 bg-red-50 p-3 rounded-lg">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Progress Bar */}
        {isLoading && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Processing...</span>
              <span className="text-gray-600">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!selectedFile || isLoading}
          className={`
            w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed
            text-white font-medium py-3 px-4 rounded-lg transition-colors
            flex items-center justify-center space-x-2
          `}
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Analyzing Document...</span>
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              <span>Analyze Document</span>
            </>
          )}
        </button>

        {/* Help Text */}
        <div className="text-xs text-gray-500 text-center">
          <p>
            Your document will be analyzed using AI-powered financial analysis agents.
            {keepFile && " The file will be stored for future reference."}
          </p>
        </div>
      </form>
    </div>
  );
};

export default FileUpload;
