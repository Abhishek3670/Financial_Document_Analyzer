import React, { useState, useEffect } from 'react';
import FileUpload from './components/ui/FileUpload';
import AnalysisResults from './components/analysis/AnalysisResults';
import AnalysisHistory from './components/analysis/AnalysisHistory';
import Documents from './components/analysis/Documents';
import Header from './components/layout/Header';
import Navigation, { NavigationTab } from './components/layout/Navigation';
import { AnalysisResponse, AnalysisHistoryItem } from './types';
import { healthCheck } from './api';
import { ToastProvider } from './components/ui/Toast';
import { AuthProvider } from './components/auth/Auth';
import './App.css';

// Define interface for upload form state
interface UploadFormState {
  selectedFile: File | null;
  query: string;
  keepFile: boolean;
  error: string | null;
}

function App() {
  const [activeTab, setActiveTab] = useState<NavigationTab>('upload');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisHistoryItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  // Lifted state to persist the entire upload form state across tab switches
  const [uploadFormState, setUploadFormState] = useState<UploadFormState>({
    selectedFile: null,
    query: 'Provide a comprehensive financial analysis of this document',
    keepFile: false,
    error: null
  });

  // Check backend health on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await healthCheck();
        setBackendStatus('online');
      } catch (error) {
        console.error('Backend health check failed:', error);
        setBackendStatus('offline');
      }
    };

    checkBackend();
  }, []);

  const handleAnalysisComplete = (result: any) => {
    setAnalysisResult(result);
    // Don't automatically switch to history, let user decide
  };

  const handleViewAnalysis = (analysis: any) => {
    setSelectedAnalysis(analysis);
    // Convert to AnalysisResponse format for display
    if (analysis.status === 'completed') {
      const analysisResponse: AnalysisResponse = {
        id: analysis.id,
        status: 'success',
        result: analysis.result || analysis.query, // Use actual result, fallback to query
        analysis_id: analysis.id,
        query: analysis.query,
        created_at: analysis.created_at,
        completed_at: analysis.completed_at,
        file_info: {
          filename: analysis.document?.original_filename || 'Unknown',
          size_mb: analysis.document ? Math.round((analysis.document.file_size / 1024 / 1024) * 100) / 100 : 0,
          processed_at: analysis.completed_at || analysis.created_at
        },
        metadata: {
          processing_id: analysis.id,
          file_type: 'PDF',
          analysis_timestamp: analysis.completed_at || analysis.created_at,
          kept_file: false
        }
      };
      setAnalysisResult(analysisResponse);
    }
  };

  const handleNewAnalysis = () => {
    setAnalysisResult(null);
    setSelectedAnalysis(null);
    // Reset the upload form state when starting a new analysis
    setUploadFormState({
      selectedFile: null,
      query: 'Provide a comprehensive financial analysis of this document',
      keepFile: false,
      error: null
    });
    setActiveTab('upload');
  };

  const handleTabChange = (tab: NavigationTab) => {
    setActiveTab(tab);
    // Clear any selected analysis when switching tabs (but keep the upload form state)
    if (tab !== 'upload') {
      setAnalysisResult(null);
      setSelectedAnalysis(null);
    }
  };

  // Render main content based on active tab and state
  const renderMainContent = () => {
    // If we have an analysis result (from upload or history), show it
    if (analysisResult) {
      return (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">Analysis Results</h2>
              <button
                onClick={handleNewAnalysis}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                New Analysis
              </button>
            </div>
            <AnalysisResults 
              result={analysisResult}
              onNewAnalysis={handleNewAnalysis}
            />
          </div>
        </div>
      );
    }

    // Otherwise show content based on active tab
    switch (activeTab) {
      case 'upload':
        return (
          <div className="space-y-6">
            <FileUpload 
              onAnalysisComplete={handleAnalysisComplete}
              uploadFormState={uploadFormState}
              onFormStateChange={setUploadFormState}
            />
          </div>
        );
      
      case 'history':
        return (
          <div className="space-y-6">
            <AnalysisHistory 
              onViewAnalysis={handleViewAnalysis}
            />
          </div>
        );
      
      case 'documents':
        return (
          <div className="space-y-6">
            <Documents />
          </div>
        );
      
      default:
        return (
          <div className="text-center py-12">
            <p className="text-gray-500">Select a tab to continue</p>
          </div>
        );
    }
  };

  return (
    <ToastProvider>
    <AuthProvider>
    <div className="flex flex-col min-h-screen bg-gray-50">
      <Header backendStatus={backendStatus} />
      
      {/* Navigation */}
      <Navigation 
        activeTab={activeTab}
        onTabChange={handleTabChange}
      />
      
      {/* Main Content */}
      <main className="flex-grow container mx-auto px-4 py-8">
        {renderMainContent()}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-6">
        <div className="container mx-auto px-4 text-center text-gray-600 text-sm">
          <p>
            Financial Document Analyzer
          </p>
        </div>
      </footer>
    </div>
    </AuthProvider>
    </ToastProvider>
  );
}

export default App;