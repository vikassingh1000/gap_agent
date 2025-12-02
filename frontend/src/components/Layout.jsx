import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Home } from 'lucide-react';

export default function Layout({ children }) {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b-2 border-green-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-4">
              <img 
                src="/images/download.jpeg" 
                alt="BP Logo" 
                className="h-12 w-auto object-contain"
                onError={(e) => {
                  // Fallback to BP text if image fails
                  e.target.style.display = 'none';
                  const parent = e.target.parentElement;
                  if (parent && !parent.querySelector('.bp-fallback')) {
                    const fallback = document.createElement('div');
                    fallback.className = 'bp-fallback w-12 h-12 bg-green-600 rounded-full flex items-center justify-center text-white font-bold text-lg';
                    fallback.textContent = 'BP';
                    parent.insertBefore(fallback, e.target.nextSibling);
                  }
                }}
              />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">BP Gap Assessment</h1>
                <p className="text-sm text-gray-600">Tax Technology & Compliance Digitization</p>
              </div>
            </div>
            <nav className="flex space-x-4">
              <Link
                to="/"
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  isActive('/') ? 'bg-green-100 text-green-700' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Home className="w-5 h-5" />
                <span>Home</span>
              </Link>
              <Link
                to="/dashboard"
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  isActive('/dashboard') ? 'bg-green-100 text-green-700' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <LayoutDashboard className="w-5 h-5" />
                <span>Dashboard</span>
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}

