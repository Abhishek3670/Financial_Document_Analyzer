import React, { useState, useEffect } from 'react';
import { BarChart3, FileText, User, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../auth/Auth';
import { EnhancedAuthModalWithReset } from '../auth/AuthEnhanced';
import { ProfileManagementDashboard } from '../auth/AuthProfileManagement';
import { useToast } from '../ui/Toast';

interface HeaderProps {
  backendStatus?: 'checking' | 'online' | 'offline';
}

const Header: React.FC<HeaderProps> = ({ backendStatus = 'checking' }) => {
  const { user, logout, refreshUser } = useAuth();
  const { showToast } = useToast();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [previousUser, setPreviousUser] = useState<typeof user>(null);

  // Monitor user changes to show welcome message
  useEffect(() => {
    if (!previousUser && user) {
      // User just logged in
      showToast(`Welcome back, ${user.full_name || user.username}!`, 'success');
      refreshUser(); // Refresh user data to ensure it's up to date
    } else if (previousUser && !user) {
      // User just logged out
      showToast('You have been logged out successfully', 'info');
    }
    setPreviousUser(user);
  }, [user, previousUser, showToast, refreshUser]);

  const handleAuthSuccess = async () => {
    // Refresh user immediately so UI updates without manual reload
    try {
      await refreshUser();
    } finally {
      setShowAuthModal(false);
    }
    // Toast will be shown by the useEffect when user state changes
  };

  const handleLogout = async () => {
    try {
      await logout();
      setShowDropdown(false);
    } catch (error) {
      showToast('Error logging out', 'error');
    }
  };

  const renderBackendStatus = () => {
    if (backendStatus === 'checking') {
      return (
        <div className="flex items-center text-yellow-700 bg-yellow-50 px-3 py-1 rounded-full text-sm">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-600 mr-2"></div>
          <span>Checking backend...</span>
        </div>
      );
    }
    
    if (backendStatus === 'offline') {
      return (
        <div className="flex items-center text-red-700 bg-red-50 px-3 py-1 rounded-full text-sm">
          <div className="w-4 h-4 bg-red-400 rounded-full mr-2"></div>
          <span>Backend Offline</span>
        </div>
      );
    }

    // Online status
    return (
      <div className="flex items-center text-green-700 bg-green-50 px-3 py-1 rounded-full text-sm">
        <div className="w-4 h-4 bg-green-400 rounded-full mr-2"></div>
        <span>Backend Online</span>
      </div>
    );
  };

  const UserDropdown = () => (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors p-2 rounded-lg hover:bg-gray-50"
      >
        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
          <User className="w-5 h-5 text-blue-600" />
        </div>
        <span className="font-medium">{user?.full_name || user?.username || 'User'}</span>
      </button>

      {showDropdown && (
        <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          <div className="py-2">
            <div className="px-4 py-2 border-b border-gray-100">
              <p className="text-sm font-medium text-gray-900">{user?.full_name}</p>
              <p className="text-sm text-gray-500">{user?.email}</p>
            </div>
            
            <button
              onClick={() => {
                setShowProfileModal(true);
                setShowDropdown(false);
              }}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center"
            >
              <Settings className="w-4 h-4 mr-2" />
              Account Settings
            </button>
            
            <button
              onClick={handleLogout}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <BarChart3 className="w-8 h-8 text-blue-600" />
                <FileText className="w-8 h-8 text-green-600" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Wingily FinAnalyzer</h1>
                <p className="text-sm text-gray-500">AI-Powered Financial Document Analysis</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Backend Status Indicator */}
              {renderBackendStatus()}
              
              {/* Authentication Section */}
              {user ? (
                <UserDropdown />
              ) : (
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  Sign In
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Authentication Modal */}
      <EnhancedAuthModalWithReset
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
        defaultMode="login"
      />

      {/* Profile Management Modal */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white rounded-t-2xl border-b border-gray-200 p-4 flex justify-between items-center">
              <h2 className="text-xl font-bold text-gray-900">Account Settings</h2>
              <button
                onClick={() => setShowProfileModal(false)}
                className="text-gray-400 hover:text-gray-600 p-1"
              >
                ✕
              </button>
            </div>
            
            <div className="p-4">
              {user && (
                <ProfileManagementDashboard
                  user={user}
                  onUpdateUser={(updatedUser) => {
                    showToast('Profile updated successfully!', 'success');
                    refreshUser();
                  }}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close dropdown */}
      {showDropdown && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setShowDropdown(false)}
        />
      )}
    </>
  );
};

export default Header;