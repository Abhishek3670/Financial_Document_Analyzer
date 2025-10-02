import React from 'react';
import { 
  Upload, 
  History, 
  FileText, 
  BarChart3, 
  Settings,
  Activity
} from 'lucide-react';

export type NavigationTab = 'upload' | 'history' | 'documents' | 'performance' | 'settings';

interface NavigationProps {
  activeTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
}

const Navigation: React.FC<NavigationProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    {
      id: 'upload' as NavigationTab,
      label: 'Upload',
      icon: Upload,
      description: 'Upload and analyze documents'
    },
    {
      id: 'history' as NavigationTab,
      label: 'History',
      icon: History,
      description: 'View analysis history'
    },
    {
      id: 'documents' as NavigationTab,
      label: 'Documents',
      icon: FileText,
      description: 'Manage your documents'
    },
    {
      id: 'performance' as NavigationTab,
      label: 'Performance',
      icon: Activity,
      description: 'Monitor system performance'
    },
  ];

  return (
    <nav className="bg-white border-b border-gray-200 dark:bg-gray-800 dark:border-gray-700">
      <div className="container mx-auto px-4">
        <div className="flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`
                  flex items-center space-x-2 py-4 px-2 border-b-2 font-medium text-sm transition-colors
                  ${isActive
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;