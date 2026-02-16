'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Home } from 'lucide-react';

interface CompactNavProps {
  title?: string;
  showBack?: boolean;
  backHref?: string;
}

export default function CompactNav({ title, showBack = true, backHref }: CompactNavProps) {
  const router = useRouter();

  const handleBack = () => {
    if (backHref) {
      router.push(backHref);
    } else {
      router.back();
    }
  };

  return (
    <div className="sticky top-0 z-40 bg-white/80 backdrop-blur-lg border-b border-gray-200/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Left: Back button and Logo */}
          <div className="flex items-center gap-4">
            {showBack && (
              <button
                onClick={handleBack}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"
              >
                <ArrowLeft className="w-4 h-4" />
                <span className="hidden sm:inline">Back</span>
              </button>
            )}
            
            <Link href="/" className="flex items-center gap-2 group">
              <Image
                src="/images/app-icon.png"
                alt="DrugDiscovery"
                width={28}
                height={28}
                className="rounded-lg group-hover:scale-105 transition-transform duration-200"
              />
              <span className="text-sm font-semibold text-gray-800 group-hover:text-blue-600 transition-colors hidden sm:inline">
                DrugDiscovery
              </span>
            </Link>
          </div>

          {/* Center: Page title */}
          {title && (
            <h1 className="text-sm font-medium text-gray-700 truncate max-w-[200px] sm:max-w-none">
              {title}
            </h1>
          )}

          {/* Right: Home button */}
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"
          >
            <Home className="w-4 h-4" />
            <span className="hidden sm:inline">Home</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
