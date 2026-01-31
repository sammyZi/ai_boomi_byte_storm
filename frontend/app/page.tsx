'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar from '@/components/SearchBar';
import { Beaker, Target, Brain, Shield } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = (query: string) => {
    setIsSearching(true);
    router.push(`/results?q=${encodeURIComponent(query)}`);
  };

  const features = [
    {
      icon: Target,
      title: 'Target Identification',
      description: 'Discover protein targets associated with diseases using Open Targets database',
    },
    {
      icon: Beaker,
      title: 'Molecule Discovery',
      description: 'Find bioactive molecules from ChEMBL with proven activity against targets',
    },
    {
      icon: Brain,
      title: 'AI Analysis',
      description: 'Get detailed insights powered by BioMistral-7B biomedical language model',
    },
    {
      icon: Shield,
      title: 'Safety Assessment',
      description: 'Evaluate drug-likeness and toxicity using RDKit cheminformatics tools',
    },
  ];

  const exampleSearches = [
    "Alzheimer's disease",
    "Parkinson's disease",
    'Type 2 diabetes',
    'Breast cancer',
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-blue-50 to-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-gray-900 mb-4">
              AI-Powered Drug Discovery
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Transform disease queries into ranked drug candidates in seconds. Integrating Open
              Targets, ChEMBL, AlphaFold, and AI-powered analysis.
            </p>
          </div>

          <div className="flex justify-center mb-8">
            <SearchBar onSearch={handleSearch} isLoading={isSearching} />
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600 mb-3">Try these examples:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {exampleSearches.map((example) => (
                <button
                  key={example}
                  onClick={() => handleSearch(example)}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 hover:border-blue-300 transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">
            How It Works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                  <feature.icon className="w-8 h-8 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-600 text-sm">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-blue-600 mb-2">8-10s</div>
              <div className="text-gray-600">Average Processing Time</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-blue-600 mb-2">3</div>
              <div className="text-gray-600">Major Biomedical Databases</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-blue-600 mb-2">32</div>
              <div className="text-gray-600">Correctness Properties Tested</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
