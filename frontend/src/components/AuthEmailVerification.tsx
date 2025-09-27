import React, { useState, useEffect } from 'react';
import { Mail, CheckCircle, AlertCircle, RefreshCw, Clock } from 'lucide-react';
import { authAPI } from '../api';

interface EmailVerificationProps {
  user?: {
    id: string;
    email?: string;
    is_verified: boolean;
  };
  onVerificationComplete?: () => void;
}

// Email Verification Status Component
export const EmailVerificationBanner: React.FC<EmailVerificationProps> = ({ 
  user, 
  onVerificationComplete 
}) => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [lastSentAt, setLastSentAt] = useState<Date | null>(null);

  if (!user || user.is_verified) {
    return null;
  }

  const handleResendVerification = async () => {
    if (!user.email) return;
    
    setLoading(true);
    setMessage('');

    try {
      await authAPI.requestEmailVerification();
      setMessage('Verification email sent successfully!');
      setLastSentAt(new Date());
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Failed to send verification email');
    } finally {
      setLoading(false);
    }
  };

  const getTimeUntilCanResend = () => {
    if (!lastSentAt) return 0;
    const timePassed = Date.now() - lastSentAt.getTime();
    const cooldown = 60 * 1000; // 1 minute cooldown
    return Math.max(0, cooldown - timePassed);
  };

  const timeUntilResend = getTimeUntilCanResend();
  const canResend = timeUntilResend === 0;

  return (
    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <AlertCircle className="h-5 w-5 text-yellow-400" />
        </div>
        <div className="ml-3 flex-1">
          <p className="text-sm text-yellow-700">
            <strong>Email verification required.</strong> Please check your email and click the verification link.
          </p>
          {message && (
            <p className={`text-sm mt-2 ${
              message.includes('success') ? 'text-green-600' : 'text-red-600'
            }`}>
              {message}
            </p>
          )}
        </div>
        <div className="flex-shrink-0">
          <button
            onClick={handleResendVerification}
            disabled={loading || !canResend}
            className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-yellow-800 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
                Sending...
              </>
            ) : !canResend ? (
              <>
                <Clock className="w-4 h-4 mr-1" />
                Wait {Math.ceil(timeUntilResend / 1000)}s
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-1" />
                Resend Email
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

// Email Verification Form Component
export const EmailVerificationForm: React.FC<{
  token?: string;
  onSuccess?: () => void;
  onError?: (error: string) => void;
}> = ({ token, onSuccess, onError }) => {
  const [verificationToken, setVerificationToken] = useState(token || '');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  // Auto-verify if token is provided
  useEffect(() => {
    if (token) {
      handleVerification(token);
    }
  }, [token]);

  const handleVerification = async (tokenToVerify?: string) => {
    const tokenValue = tokenToVerify || verificationToken;
    
    if (!tokenValue) {
      setError('Verification token is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await authAPI.verifyEmail(tokenValue);
      setSuccess(true);
      onSuccess?.();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to verify email';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleVerification();
  };

  if (success) {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-green-100 rounded-full mb-4">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Email Verified!</h2>
            <p className="text-gray-600 mt-2">Your email address has been successfully verified</p>
          </div>

          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6">
            <p className="text-sm">
              Your account is now fully activated. You can access all features of your account.
            </p>
          </div>

          <button
            onClick={onSuccess}
            className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition-colors font-medium"
          >
            Continue to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-4">
            <Mail className="w-6 h-6 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Verify Your Email</h2>
          <p className="text-gray-600 mt-2">Enter the verification code from your email</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 flex items-center">
            <AlertCircle className="w-5 h-5 mr-2" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Verification Code
            </label>
            <input
              type="text"
              value={verificationToken}
              onChange={(e) => setVerificationToken(e.target.value)}
              className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors font-mono text-center text-lg tracking-wider"
              placeholder="Enter verification code"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Verifying...
              </div>
            ) : (
              'Verify Email'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

// Email Verification Success Page Component
export const EmailVerificationSuccess: React.FC<{
  userEmail?: string;
  onContinue?: () => void;
}> = ({ userEmail, onContinue }) => {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center py-8">
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900">Welcome!</h1>
            <p className="text-gray-600 mt-2">Your email has been successfully verified</p>
          </div>

          {userEmail && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
              <div className="flex items-center">
                <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                <div>
                  <p className="text-sm font-medium text-green-800">Email Verified</p>
                  <p className="text-sm text-green-600">{userEmail}</p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <div className="flex items-center text-sm text-gray-600">
              <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
              Access to all account features
            </div>
            <div className="flex items-center text-sm text-gray-600">
              <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
              Enhanced security and notifications
            </div>
            <div className="flex items-center text-sm text-gray-600">
              <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
              Password recovery options
            </div>
          </div>

          <button
            onClick={onContinue}
            className="w-full mt-8 bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Continue to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

// Combined Email Verification Flow Component
export const EmailVerificationFlow: React.FC<{
  mode?: 'banner' | 'form' | 'success';
  user?: EmailVerificationProps['user'];
  token?: string;
  onVerificationComplete?: () => void;
}> = ({ mode = 'banner', user, token, onVerificationComplete }) => {
  const [currentMode, setCurrentMode] = useState(mode);

  if (currentMode === 'success') {
    return (
      <EmailVerificationSuccess 
        userEmail={user?.email}
        onContinue={onVerificationComplete}
      />
    );
  }

  if (currentMode === 'form' || token) {
    return (
      <EmailVerificationForm 
        token={token}
        onSuccess={() => {
          setCurrentMode('success');
          onVerificationComplete?.();
        }}
      />
    );
  }

  return (
    <EmailVerificationBanner 
      user={user}
      onVerificationComplete={() => {
        setCurrentMode('success');
        onVerificationComplete?.();
      }}
    />
  );
};

export default EmailVerificationFlow;
