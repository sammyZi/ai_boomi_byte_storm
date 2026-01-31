'use client';

import Link from 'next/link';
import { ReactNode } from 'react';
import { Pill } from 'lucide-react';
import { usePathname } from 'next/navigation';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const pathname = usePathname();
  const isResultsPage = pathname === '/results';

  return (
    <div className="min-h-screen flex flex-col">
      {/* Transparent Glass Navbar */}
      <header className="fixed top-4 left-0 right-0 z-50 px-4 sm:px-6 lg:px-8">
        <nav className="max-w-2xl mx-auto bg-white/40 backdrop-blur-2xl rounded-full shadow-lg border border-blue-200/60 px-5 py-4 ring-1 ring-blue-100/40 shadow-blue-100/30">
          <div className="flex justify-center items-center gap-10">
            {/* Logo - Left Side */}
            <Link href="/" className="flex items-center gap-2 group absolute left-5">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform shadow-lg shadow-blue-500/30">
                <Pill className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
              <span className="text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                DrugDiscovery
              </span>
            </Link>

            {/* Navigation Links - Centered */}
            <div className="flex items-center gap-6">
              <Link
                href="/"
                className="text-base font-medium text-blue-600 hover:text-blue-700 transition-colors"
              >
                Home
              </Link>
              <Link
                href="/about"
                className="text-base font-medium text-gray-700 hover:text-blue-600 transition-colors"
              >
                About
              </Link>
              <a
                href="http://10.114.2.144:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="text-base font-medium text-gray-700 hover:text-blue-600 transition-colors"
              >
                API
              </a>
            </div>
          </div>
        </nav>
      </header>

      {/* Main Content - No padding top, starts from top */}
      <main className="flex-1">{children}</main>

      {/* Compact Footer - Hidden on results page */}
      {!isResultsPage && (
        <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
                  <Pill className="w-5 h-5 text-white" />
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
      )}
    </div>
  );
}
