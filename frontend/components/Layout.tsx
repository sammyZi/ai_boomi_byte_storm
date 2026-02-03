'use client';

import Link from 'next/link';
import Image from 'next/image';
import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen flex flex-col">
      {/* Transparent Blur Navbar */}
      <header className="fixed top-4 left-0 right-0 z-50 px-4 sm:px-6 lg:px-8">
        <nav className="max-w-3xl mx-auto bg-blue-50/50 backdrop-blur-2xl rounded-full border border-gray-400/40 px-6 py-2 hover:bg-blue-50/70 hover:border-gray-500/50 transition-all duration-300">
          <div className="flex justify-between items-center">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-3 group">
              <Image
                src="/images/app-icon.png"
                alt="DrugDiscovery"
                width={40}
                height={40}
                className="rounded-xl group-hover:scale-105 transition-transform duration-200"
              />
              <span className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors duration-200">
                DrugDiscovery
              </span>
            </Link>

            {/* Navigation Links */}
            <div className="flex items-center gap-8">
              <Link
                href="/"
                className={`text-sm font-medium transition-all duration-200 hover:scale-105 ${pathname === '/' ? 'text-blue-600' : 'text-gray-700 hover:text-blue-600'}`}
              >
                Home
              </Link>
              <Link
                href="/about"
                className={`text-sm font-medium transition-all duration-200 hover:scale-105 ${pathname === '/about' ? 'text-blue-600' : 'text-gray-700 hover:text-blue-600'}`}
              >
                About
              </Link>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-gray-700 hover:text-blue-600 transition-all duration-200 hover:scale-105"
              >
                API
              </a>
            </div>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1">{children}</main>
    </div>
  );
}
