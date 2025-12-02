import { useState, useMemo } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getAssessmentHistory } from '../utils/storage';
import { format, parseISO, startOfDay, isSameDay } from 'date-fns';
import { Calendar, TrendingUp, AlertTriangle, BarChart3 } from 'lucide-react';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#3b82f6'];

export default function DashboardPage() {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const history = getAssessmentHistory();

  // Filter assessments by date
  const filteredAssessments = useMemo(() => {
    if (!selectedDate) return history;
    const targetDate = startOfDay(parseISO(selectedDate));
    return history.filter(entry => {
      const entryDate = startOfDay(parseISO(entry.timestamp));
      return isSameDay(entryDate, targetDate);
    });
  }, [history, selectedDate]);

  // Prepare data for charts
  const metricsOverTime = useMemo(() => {
    return history.map(entry => ({
      date: format(parseISO(entry.timestamp), 'MMM dd, HH:mm'),
      timestamp: entry.timestamp,
      llm_calls: entry.assessment?.metrics?.llm_calls || 0,
      latency: entry.assessment?.metrics?.latency_seconds || 0,
      search_results: entry.assessment?.metrics?.search_results_count || 0,
      total_gaps: entry.assessment?.summary?.total_gaps || 0,
      risk_score: entry.assessment?.summary?.overall_risk_score || 0,
    })).slice(0, 20); // Last 20 assessments
  }, [history]);

  const priorityDistribution = useMemo(() => {
    const distribution = { Critical: 0, High: 0, Medium: 0, Low: 0 };
    filteredAssessments.forEach(entry => {
      entry.assessment?.gaps?.forEach(gap => {
        distribution[gap.priority] = (distribution[gap.priority] || 0) + 1;
      });
    });
    return Object.entries(distribution).map(([name, value]) => ({ name, value }));
  }, [filteredAssessments]);

  const riskScoreDistribution = useMemo(() => {
    const ranges = { '0-3': 0, '4-6': 0, '7-8': 0, '9-10': 0 };
    filteredAssessments.forEach(entry => {
      entry.assessment?.gaps?.forEach(gap => {
        const score = gap.risk_score || 0;
        if (score <= 3) ranges['0-3']++;
        else if (score <= 6) ranges['4-6']++;
        else if (score <= 8) ranges['7-8']++;
        else ranges['9-10']++;
      });
    });
    return Object.entries(ranges).map(([name, value]) => ({ name, value }));
  }, [filteredAssessments]);

  const averageMetrics = useMemo(() => {
    if (filteredAssessments.length === 0) return null;
    const totals = filteredAssessments.reduce((acc, entry) => {
      const metrics = entry.assessment?.metrics || {};
      return {
        llm_calls: acc.llm_calls + (metrics.llm_calls || 0),
        latency: acc.latency + (metrics.latency_seconds || 0),
        search_results: acc.search_results + (metrics.search_results_count || 0),
        count: acc.count + 1,
      };
    }, { llm_calls: 0, latency: 0, search_results: 0, count: 0 });

    return {
      llm_calls: (totals.llm_calls / totals.count).toFixed(2),
      latency: (totals.latency / totals.count).toFixed(2),
      search_results: (totals.search_results / totals.count).toFixed(2),
    };
  }, [filteredAssessments]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-1 h-8 bg-green-600 rounded"></div>
          <h1 className="text-2xl font-bold text-gray-900">BP Gap Assessment Dashboard</h1>
        </div>
        <div className="flex items-center space-x-2">
          <Calendar className="w-5 h-5 text-gray-500" />
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="input-field w-auto"
          />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card bg-gradient-to-br from-red-50 to-red-100 border-red-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-red-700 font-medium">Critical Gaps</div>
              <div className="text-3xl font-bold text-red-900">
                {priorityDistribution.find(p => p.name === 'Critical')?.value || 0}
              </div>
            </div>
            <AlertTriangle className="w-8 h-8 text-red-600" />
          </div>
        </div>

        <div className="card bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-orange-700 font-medium">High Priority</div>
              <div className="text-3xl font-bold text-orange-900">
                {priorityDistribution.find(p => p.name === 'High')?.value || 0}
              </div>
            </div>
            <BarChart3 className="w-8 h-8 text-orange-600" />
          </div>
        </div>

        <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-blue-700 font-medium">Total Assessments</div>
              <div className="text-3xl font-bold text-blue-900">{filteredAssessments.length}</div>
            </div>
            <TrendingUp className="w-8 h-8 text-blue-600" />
          </div>
        </div>

        <div className="card bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-green-700 font-medium">Avg Latency</div>
              <div className="text-3xl font-bold text-green-900">
                {averageMetrics ? `${averageMetrics.latency}s` : '0s'}
              </div>
            </div>
            <TrendingUp className="w-8 h-8 text-green-600" />
          </div>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Priority Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Priority Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={priorityDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {priorityDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Risk Score Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Risk Score Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={riskScoreDistribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LLM Calls Over Time */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">LLM Calls Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metricsOverTime}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="llm_calls" stroke="#3b82f6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Latency Over Time */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Latency Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metricsOverTime}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="latency" stroke="#ef4444" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Search Results Over Time */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Search Results Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metricsOverTime}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="search_results" stroke="#10b981" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Total Gaps Over Time */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Total Gaps Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metricsOverTime}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="total_gaps" stroke="#f97316" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Average Metrics Table */}
      {averageMetrics && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Average Metrics</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-gray-600">Average LLM Calls</div>
              <div className="text-2xl font-bold">{averageMetrics.llm_calls}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Average Latency</div>
              <div className="text-2xl font-bold">{averageMetrics.latency}s</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Average Search Results</div>
              <div className="text-2xl font-bold">{averageMetrics.search_results}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

