import { Loader2, Database, Search, FileText, CheckCircle } from 'lucide-react';

export default function Loader({ stage = 'initializing' }) {
  const stages = {
    initializing: {
      icon: Database,
      message: 'Initializing assessment...',
      description: 'Preparing to analyze BP tax technology gaps'
    },
    searching: {
      icon: Search,
      message: 'Searching vector database...',
      description: 'Retrieving relevant data from BP and benchmark sources'
    },
    analyzing: {
      icon: FileText,
      message: 'Analyzing gaps...',
      description: 'Comparing BP with industry benchmarks (KPMG, EY, Deloitte, PWC)'
    },
    generating: {
      icon: CheckCircle,
      message: 'Generating assessment...',
      description: 'Creating comprehensive gap analysis report'
    }
  };

  const currentStage = stages[stage] || stages.initializing;
  const Icon = currentStage.icon;

  return (
    <div className="fixed inset-0 bg-white bg-opacity-95 z-50 flex items-center justify-center">
      <div className="text-center max-w-md mx-auto px-6">
        {/* BP Logo/Image */}
        <div className="mb-8 flex justify-center">
          <img 
            src="/images/download.jpeg" 
            alt="BP Logo" 
            className="h-20 w-auto object-contain"
            onError={(e) => {
              // Fallback to BP text if image fails
              e.target.style.display = 'none';
              const parent = e.target.parentElement;
              if (parent && !parent.querySelector('.bp-fallback')) {
                const fallback = document.createElement('div');
                fallback.className = 'bp-fallback text-4xl font-bold text-green-600';
                fallback.textContent = 'BP';
                parent.appendChild(fallback);
              }
            }}
          />
        </div>

        {/* Animated Loader */}
        <div className="mb-6 flex justify-center">
          <div className="relative">
            <Loader2 className="w-16 h-16 text-green-600 animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Icon className="w-8 h-8 text-green-500" />
            </div>
          </div>
        </div>

        {/* Stage Message */}
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          {currentStage.message}
        </h3>
        <p className="text-gray-600 mb-6">
          {currentStage.description}
        </p>

        {/* Progress Steps */}
        <div className="space-y-2">
          {Object.entries(stages).map(([key, stageInfo], index) => {
            const StageIcon = stageInfo.icon;
            const isActive = key === stage;
            const isCompleted = Object.keys(stages).indexOf(stage) > index;
            
            return (
              <div
                key={key}
                className={`flex items-center space-x-3 text-sm ${
                  isActive ? 'text-green-600 font-semibold' : 
                  isCompleted ? 'text-gray-400' : 'text-gray-300'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle className="w-5 h-5" />
                ) : isActive ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-gray-300" />
                )}
                <span>{stageInfo.message}</span>
              </div>
            );
          })}
        </div>

        {/* Loading Animation */}
        <div className="mt-8 flex justify-center space-x-2">
          <div className="w-2 h-2 bg-green-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
          <div className="w-2 h-2 bg-green-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 bg-green-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
        </div>
      </div>
    </div>
  );
}

