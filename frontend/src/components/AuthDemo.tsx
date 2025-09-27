import React, { useState } from 'react';
import { 
  EnhancedLoginForm, 
  EnhancedRegisterForm, 
  EnhancedAuthModal,
  EnhancedUserProfile 
} from './AuthEnhanced';

// Mock user data for demo purposes
const mockUser = {
  id: '123',
  email: 'demo@example.com',
  username: 'demouser',
  first_name: 'Demo',
  last_name: 'User',
  full_name: 'Demo User',
  is_active: true,
  is_verified: true,
  created_at: '2024-01-01T00:00:00Z',
  last_activity: '2024-01-01T00:00:00Z',
  last_login: '2024-01-01T12:00:00Z'
};

export const AuthDemo: React.FC = () => {
  const [activeDemo, setActiveDemo] = useState<'login' | 'register' | 'modal' | 'profile'>('login');
  const [showModal, setShowModal] = useState(false);

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Enhanced Authentication Components Demo
          </h1>
          <p className="text-gray-600 mb-6">
            Explore the new authentication interface with improved UX and validation
          </p>
          
          {/* Navigation */}
          <div className="flex justify-center space-x-4 mb-8">
            <button
              onClick={() => setActiveDemo('login')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                activeDemo === 'login'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              Login Form
            </button>
            <button
              onClick={() => setActiveDemo('register')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                activeDemo === 'register'
                  ? 'bg-green-600 text-white shadow-lg'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              Registration Form
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="px-6 py-2 rounded-lg font-medium bg-purple-600 text-white hover:bg-purple-700 transition-all shadow-lg"
            >
              Modal Demo
            </button>
            <button
              onClick={() => setActiveDemo('profile')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                activeDemo === 'profile'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              User Profile
            </button>
          </div>
        </div>

        {/* Demo Content */}
        <div className="max-w-2xl mx-auto">
          {activeDemo === 'login' && (
            <div>
              <h2 className="text-2xl font-semibold text-center mb-6">Enhanced Login Form</h2>
              <div className="bg-gray-50 p-8 rounded-xl">
                <EnhancedLoginForm 
                  onSuccess={() => alert('Login successful! (Demo mode)')} 
                />
              </div>
              <div className="mt-6 bg-white p-6 rounded-lg shadow-sm">
                <h3 className="font-semibold mb-3">Features:</h3>
                <ul className="list-disc list-inside space-y-2 text-gray-700">
                  <li>Real-time email validation</li>
                  <li>Show/hide password toggle</li>
                  <li>Remember me functionality</li>
                  <li>Enhanced loading states</li>
                  <li>Better error handling</li>
                  <li>Improved accessibility</li>
                </ul>
              </div>
            </div>
          )}

          {activeDemo === 'register' && (
            <div>
              <h2 className="text-2xl font-semibold text-center mb-6">Enhanced Registration Form</h2>
              <div className="bg-gray-50 p-8 rounded-xl">
                <EnhancedRegisterForm 
                  onSuccess={() => alert('Registration successful! (Demo mode)')} 
                />
              </div>
              <div className="mt-6 bg-white p-6 rounded-lg shadow-sm">
                <h3 className="font-semibold mb-3">Features:</h3>
                <ul className="list-disc list-inside space-y-2 text-gray-700">
                  <li>Comprehensive field validation</li>
                  <li>Real-time password strength indicator</li>
                  <li>Password confirmation matching</li>
                  <li>Username format validation</li>
                  <li>Email format validation</li>
                  <li>Visual feedback for all validations</li>
                </ul>
              </div>
            </div>
          )}

          {activeDemo === 'profile' && (
            <div>
              <h2 className="text-2xl font-semibold text-center mb-6">Enhanced User Profile</h2>
              <div className="bg-gray-50 p-8 rounded-xl">
                <EnhancedUserProfile 
                  user={mockUser}
                  onLogout={() => alert('Logged out! (Demo mode)')}
                />
              </div>
              <div className="mt-6 bg-white p-6 rounded-lg shadow-sm">
                <h3 className="font-semibold mb-3">Features:</h3>
                <ul className="list-disc list-inside space-y-2 text-gray-700">
                  <li>Modern gradient header design</li>
                  <li>Organized information layout</li>
                  <li>Status indicators with colors</li>
                  <li>Last login tracking</li>
                  <li>Profile editing capabilities (coming soon)</li>
                  <li>Responsive design</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Features Overview */}
        <div className="mt-16 bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-center mb-8">Authentication System Overview</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="text-center p-6 bg-blue-50 rounded-lg">
              <div className="w-12 h-12 bg-blue-600 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <span className="text-white font-bold">🔐</span>
              </div>
              <h3 className="font-semibold mb-2">Secure Authentication</h3>
              <p className="text-sm text-gray-600">JWT-based authentication with proper token management</p>
            </div>
            
            <div className="text-center p-6 bg-green-50 rounded-lg">
              <div className="w-12 h-12 bg-green-600 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <span className="text-white font-bold">✓</span>
              </div>
              <h3 className="font-semibold mb-2">Form Validation</h3>
              <p className="text-sm text-gray-600">Real-time validation with user-friendly error messages</p>
            </div>
            
            <div className="text-center p-6 bg-purple-50 rounded-lg">
              <div className="w-12 h-12 bg-purple-600 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <span className="text-white font-bold">📱</span>
              </div>
              <h3 className="font-semibold mb-2">Responsive Design</h3>
              <p className="text-sm text-gray-600">Mobile-first design with modern UI components</p>
            </div>
            
            <div className="text-center p-6 bg-yellow-50 rounded-lg">
              <div className="w-12 h-12 bg-yellow-600 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <span className="text-white font-bold">🎯</span>
              </div>
              <h3 className="font-semibold mb-2">User Experience</h3>
              <p className="text-sm text-gray-600">Enhanced UX with loading states and visual feedback</p>
            </div>
            
            <div className="text-center p-6 bg-red-50 rounded-lg">
              <div className="w-12 h-12 bg-red-600 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <span className="text-white font-bold">🛡️</span>
              </div>
              <h3 className="font-semibold mb-2">Password Security</h3>
              <p className="text-sm text-gray-600">Password strength indicators and security requirements</p>
            </div>
            
            <div className="text-center p-6 bg-indigo-50 rounded-lg">
              <div className="w-12 h-12 bg-indigo-600 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <span className="text-white font-bold">♿</span>
              </div>
              <h3 className="font-semibold mb-2">Accessibility</h3>
              <p className="text-sm text-gray-600">ARIA labels and keyboard navigation support</p>
            </div>
          </div>
        </div>
      </div>

      {/* Modal Demo */}
      <EnhancedAuthModal 
        isOpen={showModal}
        onClose={() => setShowModal(false)}
      />
    </div>
  );
};

export default AuthDemo;
