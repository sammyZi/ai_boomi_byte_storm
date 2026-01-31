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
    </div>
  );
}
