import { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, MessageSquare, Send, User } from 'lucide-react';
import { getComments, saveComment } from '../utils/storage';
import { format } from 'date-fns';

export default function GapDetailPage() {
  const { gapId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [gap, setGap] = useState(location.state?.gap || null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    if (gap) {
      setComments(getComments(gap.gap_id));
    }
  }, [gap]);

  const handleAddComment = () => {
    if (!newComment.trim()) return;
    const comment = saveComment(gap.gap_id, newComment);
    setComments([...comments, comment]);
    setNewComment('');
  };

  if (!gap) {
    return (
      <div className="card">
        <p className="text-gray-600">Gap not found</p>
        <button onClick={() => navigate('/')} className="btn-primary mt-4">
          Back to Home
        </button>
      </div>
    );
  }

  const priorityColors = {
    Critical: 'badge-critical',
    High: 'badge-high',
    Medium: 'badge-medium',
    Low: 'badge-low',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/')}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Gaps</span>
        </button>
      </div>

      {/* Gap Details */}
      <div className="card">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{gap.gap_id}</h1>
            <p className="text-lg text-gray-700">{gap.description}</p>
          </div>
          <div className="flex items-center space-x-3">
            <span className={`${priorityColors[gap.priority]} text-sm`}>
              {gap.priority}
            </span>
            <div className="text-right">
              <div className="text-2xl font-bold text-green-600">{gap.risk_score}/10</div>
              <div className="text-xs text-gray-500">Risk Score</div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Current State */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Current State</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-700 whitespace-pre-wrap">{gap.current_state}</p>
            </div>
          </div>

          {/* Target State */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Target State</h3>
            <div className="bg-green-50 rounded-lg p-4 border-l-4 border-green-500">
              <p className="text-gray-700 whitespace-pre-wrap">{gap.target_state}</p>
            </div>
          </div>

          {/* Recommendations */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Recommendations</h3>
            <ul className="space-y-2">
              {gap.recommendations?.map((rec, index) => (
                <li key={index} className="flex items-start space-x-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-sm font-semibold mt-0.5">
                    {index + 1}
                  </span>
                  <span className="text-gray-700">{rec}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Benchmark Source */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Benchmark Source</h3>
            <div className="flex flex-wrap gap-2">
              {gap.benchmark_source?.split(',').map((source, index) => (
                <span
                  key={index}
                  className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm font-medium"
                >
                  {source.trim()}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Comments Section */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-4">
          <MessageSquare className="w-5 h-5 text-gray-600" />
          <h2 className="text-xl font-semibold">Comments & Updates</h2>
          <span className="text-sm text-gray-500">({comments.length})</span>
        </div>

        {/* Add Comment */}
        <div className="mb-6">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add a comment or update..."
            className="input-field mb-2"
            rows="3"
          />
          <button onClick={handleAddComment} className="btn-primary flex items-center space-x-2">
            <Send className="w-4 h-4" />
            <span>Add Comment</span>
          </button>
        </div>

        {/* Comments List */}
        <div className="space-y-4">
          {comments.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No comments yet. Be the first to comment!</p>
          ) : (
            comments.map((comment) => (
              <div key={comment.id} className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <User className="w-4 h-4 text-gray-500" />
                    <span className="font-medium text-gray-900">{comment.author}</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {format(new Date(comment.timestamp), 'MMM dd, yyyy HH:mm')}
                  </span>
                </div>
                <p className="text-gray-700 whitespace-pre-wrap">{comment.text}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

