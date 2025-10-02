import React, { useState, useEffect } from 'react';
import { performanceAPI } from '../../api';
import { BarChart3, Clock, CheckCircle, AlertCircle, RefreshCw, TrendingUp, Zap, BarChart } from 'lucide-react';
import { BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

const PerformanceDashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await performanceAPI.getDashboardData();
      setDashboardData(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err: any) {
      setError(err.message || 'Failed to load performance data');
      console.error('Performance dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    fetchData();
  };

  const formatTime = (seconds: number) => {
    if (seconds < 1) return `${(seconds * 1000).toFixed(2)}ms`;
    return `${seconds.toFixed(2)}s`;
  };

  if (loading && !dashboardData) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertCircle className="h-5 w-5 text-red-400" />
          </div>
          <div className="ml-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const llmMetrics = dashboardData?.llm_metrics || {};
  const crewPerformance = dashboardData?.crew_performance || {};
  const toolPerformance = dashboardData?.tool_performance || {};

  // Prepare data for charts
  const crewPerformanceData = Object.entries(crewPerformance).map(([name, metrics]: [string, any]) => ({
    name,
    averageTime: metrics.average_time,
    executions: metrics.total_executions
  }));

  const toolPerformanceData = Object.entries(toolPerformance).map(([name, metrics]: [string, any]) => ({
    name,
    averageTime: metrics.average_time,
    executions: metrics.total_executions
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Performance Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor system performance and resource utilization
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex items-center space-x-3">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Last updated: {lastUpdated}
          </div>
          <button
            onClick={handleRefresh}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </button>
        </div>
      </div>

      {/* LLM Metrics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <BarChart3 className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Calls</h3>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {llmMetrics.total_calls || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <TrendingUp className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Success Rate</h3>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {llmMetrics.success_rate ? `${(llmMetrics.success_rate * 100).toFixed(1)}%` : '0%'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
              <Zap className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Avg Latency</h3>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {llmMetrics.average_latency_ms ? `${llmMetrics.average_latency_ms.toFixed(2)}ms` : '0ms'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <CheckCircle className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Successful</h3>
              <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                {llmMetrics.successful_calls || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* LLM Metrics Chart */}
      {llmMetrics.recent_metrics && llmMetrics.recent_metrics.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
              <BarChart className="h-5 w-5 mr-2 text-blue-500" />
              LLM Performance Trend
            </h2>
          </div>
          <div className="p-6 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={llmMetrics.recent_metrics.map((metric: any, index: number) => ({
                  name: `Call ${index + 1}`,
                  latency: metric.latency_ms,
                  status: metric.status
                }))}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="latency" 
                  stroke="#3b82f6" 
                  activeDot={{ r: 8 }} 
                  name="Latency (ms)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Crew Performance */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <Clock className="h-5 w-5 mr-2 text-blue-500" />
            Crew Performance
          </h2>
        </div>
        <div className="p-6">
          {Object.keys(crewPerformance).length === 0 ? (
            <div className="text-center py-4">
              <p className="text-gray-500 dark:text-gray-400">No crew performance data available</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Crew Performance Table */}
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Crew</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Executions</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Avg Time</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Min Time</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Max Time</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {Object.entries(crewPerformance).map(([crewName, metrics]: [string, any]) => (
                      <tr key={crewName} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                          {crewName}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {metrics.total_executions}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {formatTime(metrics.average_time)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {formatTime(metrics.min_time)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {formatTime(metrics.max_time)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Crew Performance Chart */}
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsBarChart
                    data={crewPerformanceData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={60} />
                    <YAxis label={{ value: 'Avg Time (s)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip formatter={(value) => [formatTime(Number(value)), 'Average Time']} />
                    <Legend />
                    <Bar dataKey="averageTime" name="Average Time" fill="#3b82f6" />
                  </RechartsBarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tool Performance */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <CheckCircle className="h-5 w-5 mr-2 text-purple-500" />
            Tool Performance
          </h2>
        </div>
        <div className="p-6">
          {Object.keys(toolPerformance).length === 0 ? (
            <div className="text-center py-4">
              <p className="text-gray-500 dark:text-gray-400">No tool performance data available</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Tool</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Executions</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Avg Time</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Min Time</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Max Time</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {Object.entries(toolPerformance).map(([toolName, metrics]: [string, any]) => (
                    <tr key={toolName} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {toolName}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {metrics.total_executions}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatTime(metrics.average_time)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatTime(metrics.min_time)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatTime(metrics.max_time)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PerformanceDashboard;