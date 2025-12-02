import { ArrowRight, AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react';

const priorityIcons = {
  Critical: AlertTriangle,
  High: AlertCircle,
  Medium: Info,
  Low: CheckCircle,
};

const priorityColors = {
  Critical: 'badge-critical',
  High: 'badge-high',
  Medium: 'badge-medium',
  Low: 'badge-low',
};

export default function GapTable({ gaps, onGapClick }) {
  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4">Identified Gaps</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Gap ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk Score
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Benchmark Source
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {gaps.map((gap) => {
              const Icon = priorityIcons[gap.priority] || Info;
              return (
                <tr
                  key={gap.gap_id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => onGapClick(gap.gap_id)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{gap.gap_id}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900 max-w-md truncate">
                      {gap.description}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`${priorityColors[gap.priority]} flex items-center space-x-1 w-fit`}>
                      <Icon className="w-3 h-3" />
                      <span>{gap.priority}</span>
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="text-sm font-semibold text-gray-900">{gap.risk_score}/10</div>
                      <div className="ml-2 w-24 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            gap.risk_score >= 8
                              ? 'bg-red-600'
                              : gap.risk_score >= 6
                              ? 'bg-orange-600'
                              : gap.risk_score >= 4
                              ? 'bg-yellow-600'
                              : 'bg-blue-600'
                          }`}
                          style={{ width: `${(gap.risk_score / 10) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-600">{gap.benchmark_source || 'N/A'}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button className="text-green-600 hover:text-green-700 flex items-center space-x-1">
                      <span className="text-sm font-medium">View Details</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

