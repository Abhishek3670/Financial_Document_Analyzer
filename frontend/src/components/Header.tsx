import React from 'react';
import { BarChart3, FileText } from 'lucide-react';

const Header: React.FC = () => {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-8 h-8 text-blue-600" />
              <FileText className="w-8 h-8 text-green-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">FinAnalyzer</h1>
              <p className="text-sm text-gray-500">AI-Powered Financial Analysis</p>
            </div>
          </div>
          
          <nav className="hidden md:flex space-x-6">
            <a href="javascript:void(0)" className="text-gray-600 hover:text-blue-600 transition-colors">
              Dashboard
            </a>
            <a href="javascript:void(0)" className="text-gray-600 hover:text-blue-600 transition-colors">
              About
            </a>
            <a href="javascript:void(0)" className="text-gray-600 hover:text-blue-600 transition-colors">
              Help
            </a>
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;
