import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { assessGaps } from '../services/api';
import { saveAssessmentHistory } from '../utils/storage';
import GapTable from '../components/GapTable';
import Loader from '../components/Loader';
import { Search, AlertCircle } from 'lucide-react';

export default function HomePage() {
  const [query, setQuery] = useState('What are the gaps in BP tax technology compared to industry benchmarks?');
  const [forceExtraction, setForceExtraction] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState('initializing');
  const [error, setError] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setLoadingStage('initializing');
    setError(null);
    setAssessment(null);

    try {
      // Simulate stage progression
      setTimeout(() => setLoadingStage('searching'), 500);
      setTimeout(() => setLoadingStage('analyzing'), 2000);
      setTimeout(() => setLoadingStage('generating'), 4000);

      const result = await assessGaps(query, forceExtraction);
      setAssessment(result.assessment);
      
      // Save to history for dashboard
      saveAssessmentHistory(result.assessment);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to assess gaps');
    } finally {
      setLoading(false);
      setLoadingStage('initializing');
    }
  };

  const handleGapClick = (gapId) => {
    navigate(`/gap/${gapId}`, { state: { gap: assessment.gaps.find(g => g.gap_id === gapId), assessment } });
  };

  // Sort gaps by priority: Critical > High > Medium > Low
  const sortedGaps = assessment?.gaps ? [...assessment.gaps].sort((a, b) => {
    const priorityOrder = { Critical: 0, High: 1, Medium: 2, Low: 3 };
    return priorityOrder[a.priority] - priorityOrder[b.priority];
  }) : [];

  return (
    <div className="space-y-6">
      {/* Loading Overlay */}
      {loading && <Loader stage={loadingStage} />}

      {/* Query Form */}
      <div className="card border-l-4 border-green-600">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-1 h-8 bg-green-600 rounded"></div>
          <h2 className="text-xl font-semibold text-gray-900">BP Gap Assessment Query</h2>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Query
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="input-field"
              rows="3"
              placeholder="Enter your gap assessment query..."
              required
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={forceExtraction}
                  onChange={(e) => setForceExtraction(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                <span className="ml-3 text-sm font-medium text-gray-700">
                  Force Extraction
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Search className="w-4 h-4" />
              <span>{loading ? 'Processing...' : 'Assess Gaps'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Error Message */}
      {error && (
        <div className="card bg-red-50 border-red-200">
          <div className="flex items-center space-x-2 text-red-800">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">Error: {error}</span>
          </div>
        </div>
      )}

      {/* Assessment Summary */}
      {assessment && assessment.summary && (
        <div className="card bg-gradient-to-r from-green-50 to-yellow-50 border-green-200">
          <h3 className="text-lg font-semibold mb-4">Assessment Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-2xl font-bold text-gray-900">{assessment.summary.total_gaps}</div>
              <div className="text-sm text-gray-600">Total Gaps</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">{assessment.summary.critical_gaps}</div>
              <div className="text-sm text-gray-600">Critical</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">{assessment.summary.high_priority_gaps}</div>
              <div className="text-sm text-gray-600">High Priority</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{assessment.summary.overall_risk_score}/10</div>
              <div className="text-sm text-gray-600">Risk Score</div>
            </div>
          </div>
        </div>
      )}

      {/* Gaps Table */}
      {assessment && sortedGaps.length > 0 && (
        <GapTable gaps={sortedGaps} onGapClick={handleGapClick} />
      )}

      {/* Metrics */}
      {assessment && assessment.metrics && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Performance Metrics</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-600">LLM Calls</div>
              <div className="text-xl font-semibold">{assessment.metrics.llm_calls}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Latency</div>
              <div className="text-xl font-semibold">{assessment.metrics.latency_seconds}s</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Search Results</div>
              <div className="text-xl font-semibold">{assessment.metrics.search_results_count}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Comparisons</div>
              <div className="text-xl font-semibold">{assessment.metrics.comparison_count}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

