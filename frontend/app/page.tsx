'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import SearchBar from '@/components/SearchBar';

export default function HomePage() {
  const router = useRouter();
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = (query: string) => {
    if (query && query.length >= 2) {
      setIsSearching(true);
      setTimeout(() => {
        router.push(`/results?q=${encodeURIComponent(query)}`);
      }, 100);
    }
  };

  const exampleSearches = [
    "Alzheimer's disease",
    "Parkinson's disease",
    'Type 2 diabetes',
    'Breast cancer',
  ];

  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section - Exactly 100vh */}
      <section className="h-screen flex items-center relative overflow-hidden">
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50/50 to-indigo-50/50"></div>

        {/* Animated floating orbs */}
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-blue-200/40 rounded-full blur-3xl animate-blob"></div>
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-indigo-200/40 rounded-full blur-3xl animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-20 left-1/3 w-72 h-72 bg-purple-200/30 rounded-full blur-3xl animate-blob animation-delay-4000"></div>

        {/* Subtle grid pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#94a3b840_1px,transparent_1px),linear-gradient(to_bottom,#94a3b840_1px,transparent_1px)] bg-[size:3rem_3rem]"></div>

        {/* Radial gradient overlay */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(255,255,255,0.8)_70%)]"></div>

        <div className="relative w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div>
              {/* Heading */}
              <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-6 leading-tight">
                Transform Disease Queries into
                <span className="block text-blue-600 mt-2">Drug Candidates</span>
              </h1>

              {/* Description */}
              <p className="text-lg text-gray-600 max-w-md mb-8 leading-relaxed">
                Discover ranked drug candidates in seconds using Open Targets, ChEMBL,
                AlphaFold, and AI-powered molecular analysis.
              </p>

              {/* Search Bar */}
              <div className="mb-6">
                <SearchBar onSearch={handleSearch} isLoading={isSearching} />
              </div>

              {/* Example Searches */}
              <div>
                <p className="text-sm text-gray-500 mb-3">Try an example:</p>
                <div className="flex flex-wrap gap-2">
                  {exampleSearches.map((example) => (
                    <button
                      key={example}
                      onClick={() => handleSearch(example)}
                      className="px-4 py-2 bg-white/80 hover:bg-white border border-gray-200 hover:border-blue-300 rounded-lg text-sm text-gray-600 hover:text-blue-600 transition-all shadow-sm hover:shadow-md"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Content - Image */}
            <div className="relative hidden lg:flex justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-200/20 rounded-2xl blur-2xl transform rotate-3"></div>
                <Image
                  src="/images/scientist-lab.png"
                  alt="Scientist analyzing molecular data"
                  width={520}
                  height={520}
                  className="relative rounded-2xl shadow-2xl border border-white/50"
                  priority
                />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
