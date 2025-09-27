import React, { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import AnalysisResults from './components/AnalysisResults';
import AnalysisHistory from './components/AnalysisHistory';
import Header from './components/Header';
import Navigation, { NavigationTab } from './components/Navigation';
import { AnalysisResponse, AnalysisHistoryItem } from './types';
import { healthCheck } from './api';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState<NavigationTab>('upload');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisHistoryItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

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

  const handleAnalysisComplete = (result: AnalysisResponse) => {
    setAnalysisResult(result);
    // Don't automatically switch to history, let user decide
  };

  const handleViewAnalysis = (analysis: AnalysisHistoryItem) => {
    setSelectedAnalysis(analysis);
    // Convert to AnalysisResponse format for display
    if (analysis.status === 'completed') {
      const analysisResponse: AnalysisResponse = {
        status: 'success',
        analysis_id: analysis.id,
        document_id: analysis.document_id,
        user_id: analysis.user_id,
        file_info: {
          filename: analysis.document?.original_filename || 'Unknown',
          size_mb: analysis.document ? Math.round((analysis.document.file_size / 1024 / 1024) * 100) / 100 : 0,
          processed_at: analysis.completed_at || analysis.started_at
        },
        query: analysis.query,
        analysis: analysis.result, // This is the key fix - use result field from database
        metadata: {
          processing_id: analysis.id,
          file_type: analysis.document?.file_type || 'PDF',
          analysis_timestamp: analysis.completed_at || analysis.started_at,
          kept_file: analysis.document?.is_stored_permanently || false
        }
      };
      setAnalysisResult(analysisResponse);
    }
  };

  const handleNewAnalysis = () => {
    setAnalysisResult(null);
    setSelectedAnalysis(null);
    setActiveTab('upload');
  };

  const handleTabChange = (tab: NavigationTab) => {
    setActiveTab(tab);
    // Clear any selected analysis when switching tabs
    if (tab !== 'upload') {
      setAnalysisResult(null);
      setSelectedAnalysis(null);
    }
  };

  // Backend status indicator
  const renderBackendStatus = () => {
    if (backendStatus === 'checking') {
      return (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-yellow-600"></div>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700">
                Checking backend connection...
              </p>
            </div>
          </div>
        </div>
      );
    }
    
    if (backendStatus === 'offline') {
      return (
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <div className="w-5 h-5 bg-red-400 rounded-full"></div>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">
                Backend server is offline. Please make sure the server is running on port 8000.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return null;
  };

  // Render main content based on active tab and state
  const renderMainContent = () => {
    // If viewing analysis results, show them regardless of active tab
    if (analysisResult) {
      return (
        <AnalysisResults 
          result={analysisResult}
          onNewAnalysis={handleNewAnalysis}
        />
      );
    }

    // Otherwise show content based on active tab
    switch (activeTab) {
      case 'upload':
        return (
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold text-gray-900 mb-4">
                Financial Document Analyzer
              </h1>
              <p className="text-xl text-gray-600">
                Upload your financial documents and get AI-powered insights
              </p>
            </div>
            
            <FileUpload 
              onAnalysisComplete={handleAnalysisComplete}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
            />
          </div>
        );

      case 'history':
        return (
          <div className="max-w-6xl mx-auto">
            <AnalysisHistory 
              onViewAnalysis={handleViewAnalysis}
            />
          </div>
        );

      case 'documents':
        return (
          <div className="max-w-6xl mx-auto">
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Document Management</h2>
              <p className="text-gray-600">
                Document management interface coming soon...
              </p>
            </div>
          </div>
        );

      case 'analytics':
        return (
          <div className="max-w-6xl mx-auto">
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Analytics Dashboard</h2>
              <p className="text-gray-600">
                Analytics and statistics dashboard coming soon...
              </p>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      {/* Backend status indicator */}
      {renderBackendStatus()}
      
      {/* Navigation */}
      <Navigation 
        activeTab={activeTab}
        onTabChange={handleTabChange}
      />
      
      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {renderMainContent()}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-6 mt-12">
        <div className="container mx-auto px-4 text-center text-gray-600 text-sm">
          <p>
            Financial Document Analyzer v2.0 • 
            Backend: <span className={`font-medium ${backendStatus === 'online' ? 'text-green-600' : 'text-red-600'}`}>
              {backendStatus === 'online' ? 'Online' : backendStatus === 'offline' ? 'Offline' : 'Checking...'}
            </span>
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
