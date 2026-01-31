'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar from '@/components/SearchBar';
import { Target, Brain, Shield, Database, Sparkles, TrendingUp, CheckCircle, Pill } from 'lucide-react';

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

  const features = [
    {
      icon: Target,
      title: 'Target Identification',
      description: 'Discover protein targets associated with diseases using Open Targets database',
      color: 'bg-primary-600',
      lightColor: 'bg-primary-50',
      textColor: 'text-primary-600',
    },
    {
      icon: Database,
      title: 'Molecule Discovery',
      description: 'Find bioactive molecules from ChEMBL with proven activity against targets',
      color: 'bg-purple-600',
      lightColor: 'bg-purple-50',
      textColor: 'text-purple-600',
    },
    {
      icon: Brain,
      title: 'AI Analysis',
      description: 'Get detailed insights powered by BioMistral-7B biomedical language model',
      color: 'bg-teal-600',
      lightColor: 'bg-teal-50',
      textColor: 'text-teal-600',
    },
    {
      icon: Shield,
      title: 'Safety Assessment',
      description: 'Evaluate drug-likeness and toxicity using RDKit cheminformatics tools',
      color: 'bg-green-600',
      lightColor: 'bg-green-50',
      textColor: 'text-green-600',
    },
  ];

  const exampleSearches = [
    "Alzheimer's disease",
    "Parkinson's disease",
    'Type 2 diabetes',
    'Breast cancer',
  ];

  const benefits = [
    'Comprehensive target-to-drug pipeline',
    'AI-powered candidate analysis',
    'Real-time toxicity assessment',
    'AlphaFold protein structures',
  ];

  return (
    <div>
      {/* Hero Section with smooth subtle background */}
      <div className="relative overflow-hidden min-h-screen flex items-center pt-24">
        {/* Base gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-indigo-50"></div>
        
        {/* Animated color orbs - smooth and spread */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-20 left-1/4 w-[500px] h-[500px] bg-gradient-to-br from-blue-300 to-blue-200 rounded-full mix-blend-multiply filter blur-[120px] animate-blob"></div>
          <div className="absolute top-1/3 right-1/4 w-[450px] h-[450px] bg-gradient-to-br from-indigo-300 to-indigo-200 rounded-full mix-blend-multiply filter blur-[120px] animate-blob animation-delay-2000"></div>
          <div className="absolute bottom-1/4 left-1/3 w-[400px] h-[400px] bg-gradient-to-br from-purple-300 to-purple-200 rounded-full mix-blend-multiply filter blur-[120px] animate-blob animation-delay-4000"></div>
        </div>
        
        {/* Decorative grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#3b82f615_1px,transparent_1px),linear-gradient(to_bottom,#3b82f615_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>
        
        {/* Subtle vignette */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/40"></div>
        
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 leading-tight tracking-tight">
              Transform Disease Queries into
              <span className="block text-blue-600 mt-1">Drug Candidates</span>
            </h1>
            
            <p className="text-base text-gray-600 max-w-xl mx-auto leading-relaxed mb-10">
              Discover ranked drug candidates in seconds using Open Targets, ChEMBL, 
              AlphaFold, and AI-powered analysis.
            </p>
          </div>

          {/* Search Bar */}
          <div className="flex justify-center mb-10">
            <SearchBar onSearch={handleSearch} isLoading={isSearching} />
          </div>

          {/* Example Searches */}
          <div className="text-center mb-12">
            <p className="text-xs text-gray-500 mb-2 font-medium">Try an example:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {exampleSearches.map((example) => (
                <button
                  key={example}
                  onClick={() => handleSearch(example)}
                  className="px-2.5 py-1 bg-white border border-gray-200 rounded-md text-xs text-gray-700 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 transition-all font-medium shadow-sm"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          {/* Minimal Benefits */}
          <div className="flex flex-wrap justify-center gap-6 text-xs text-gray-500">
            {benefits.map((benefit, index) => (
              <div key={index} className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />
                <span>{benefit}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
