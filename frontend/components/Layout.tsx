import Link from 'next/link';
import { ReactNode } from 'react';
import { Beaker, Home, Info, FileText } from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Enhanced Floating Navbar */}
      <header className="sticky top-6 z-50 px-4 sm:px-6 lg:px-8">
        <nav className="max-w-5xl mx-auto bg-white/95 backdrop-blur-lg rounded-2xl shadow-2xl border border-gray-200/50 hover:shadow-3xl transition-all duration-300">
          <div className="flex justify-center items-center h-16 px-6 gap-8">
            {/* Logo with glow effect */}
            <Link href="/" className="flex items-center gap-3 group">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-600 rounded-xl blur-md opacity-40 group-hover:opacity-60 transition-opacity"></div>
                <div className="relative w-11 h-11 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                  <Beaker className="w-6 h-6 text-white" strokeWidth={2.5} />
                </div>
              </div>
              <div className="hidden sm:block">
                <span className="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                  DrugDiscovery
                </span>
                <span className="block text-xs text-gray-500 font-medium -mt-0.5">AI Platform</span>
              </div>
            </Link>

            {/* Navigation Links - centered, no background */}
            <div className="flex items-center gap-1">
              <Link
                href="/"
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-blue-600 rounded-lg transition-all group"
              >
                <Home className="w-4 h-4 group-hover:scale-110 transition-transform" />
                <span className="hidden sm:inline">Home</span>
              </Link>
              <Link
                href="/about"
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-blue-600 rounded-lg transition-all group"
              >
                <Info className="w-4 h-4 group-hover:scale-110 transition-transform" />
                <span className="hidden sm:inline">About</span>
              </Link>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-blue-600 rounded-lg transition-all group"
              >
                <FileText className="w-4 h-4 group-hover:scale-110 transition-transform" />
                <span className="hidden sm:inline">API</span>
              </a>
            </div>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1">{children}</main>

      {/* Compact Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <div className="w-8 h-8 bg-blue-600 rounded-xl flex items-center justify-center">
                  <Beaker className="w-5 h-5 text-white" />
                </div>
                <span className="font-bold text-gray-900">DrugDiscovery AI</span>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed">
                AI-powered drug discovery platform integrating Open Targets, ChEMBL, and
                AlphaFold databases.
              </p>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Data Sources</h3>
              <ul className="space-y-2">
                <li>
                  <a
                    href="https://platform.opentargets.org/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-600 hover:text-blue-600 transition-colors"
                  >
                    Open Targets Platform
                  </a>
                </li>
                <li>
                  <a
                    href="https://www.ebi.ac.uk/chembl/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-600 hover:text-blue-600 transition-colors"
                  >
                    ChEMBL Database
                  </a>
                </li>
                <li>
                  <a
                    href="https://alphafold.ebi.ac.uk/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-600 hover:text-blue-600 transition-colors"
                  >
                    AlphaFold Database
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Contact</h3>
              <p className="text-sm text-gray-600 leading-relaxed">
                For questions or support, contact us at{' '}
                <a
                  href="mailto:support@drugdiscovery.example.com"
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  support@drugdiscovery.example.com
                </a>
              </p>
            </div>
          </div>
          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-500 text-center">
              © {new Date().getFullYear()} AI-Powered Drug Discovery Platform. For research purposes only.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
