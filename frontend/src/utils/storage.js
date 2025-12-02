// Local storage utilities for comments and updates

export const saveComment = (gapId, comment) => {
  const comments = getComments(gapId);
  const newComment = {
    id: Date.now().toString(),
    text: comment,
    author: 'Current User', // In production, get from auth
    timestamp: new Date().toISOString(),
  };
  comments.push(newComment);
  localStorage.setItem(`gap_${gapId}_comments`, JSON.stringify(comments));
  return newComment;
};

export const getComments = (gapId) => {
  const stored = localStorage.getItem(`gap_${gapId}_comments`);
  return stored ? JSON.parse(stored) : [];
};

export const saveAssessmentHistory = (assessment) => {
  const history = getAssessmentHistory();
  const entry = {
    id: Date.now().toString(),
    timestamp: new Date().toISOString(),
    assessment,
  };
  history.unshift(entry);
  // Keep last 100 assessments
  if (history.length > 100) {
    history.pop();
  }
  localStorage.setItem('assessment_history', JSON.stringify(history));
  return entry;
};

export const getAssessmentHistory = () => {
  const stored = localStorage.getItem('assessment_history');
  return stored ? JSON.parse(stored) : [];
};

export const getAssessmentByDate = (date) => {
  const history = getAssessmentHistory();
  return history.filter(entry => {
    const entryDate = new Date(entry.timestamp).toDateString();
    return entryDate === new Date(date).toDateString();
  });
};

