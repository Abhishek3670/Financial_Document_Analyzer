import React from 'react';
import { 
  EnhancedAuthModal, 
  EnhancedUserProfile 
} from './AuthEnhanced';
import { useAuth } from './Auth';

/**
 * Integration example showing how to use enhanced auth components
 * with the existing auth system
 */
export const AuthIntegration: React.FC = () => {
  const { user, logout } = useAuth();
  const [showAuthModal, setShowAuthModal] = React.useState(false);

  if (user) {
    // User is logged in - show enhanced profile
    return (
      <div className="p-6">
        <EnhancedUserProfile 
          user={user}
          onLogout={logout}
        />
      </div>
    );
  }

  // User is not logged in - show auth modal trigger
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Welcome to Wingily
        </h1>
        <p className="text-gray-600 mb-8">
          Please sign in to access your financial document analyzer
        </p>
        
        <button
          onClick={() => setShowAuthModal(true)}
          className="bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors shadow-lg"
        >
          Get Started
        </button>
      </div>

      <EnhancedAuthModal 
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        defaultMode="login"
      />
    </div>
  );
};

export default AuthIntegration;
