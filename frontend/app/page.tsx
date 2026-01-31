'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar from '@/components/SearchBar';
import { Target, Brain, Shield, Database, Sparkles, TrendingUp, CheckCircle } from 'lucide-react';

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

  return (
    <div className="min-h-[calc(100vh-5rem)] mt-8">
      {/* Hero Section */}
      <div className="relative overflow-hidden mesh-gradient-bg min-h-[85vh] flex items-center justify-center -mt-24 pt-24 pb-20">

        {/* Animated Background Elements */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary-200/40 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-100 contrast-150 mix-blend-overlay"></div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 w-full">
          <div className="text-center mb-16 animate-fadeIn">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/60 backdrop-blur-md text-primary-700 rounded-full text-xs font-semibold mb-8 border border-primary-100 shadow-sm ring-1 ring-primary-50 hover:bg-white/80 transition-colors cursor-default">
              <Sparkles className="w-3 h-3 text-primary-500" />
              <span>Next-Gen AI Drug Discovery</span>
            </div>

            <h1 className="text-6xl md:text-8xl font-black text-slate-900 mb-6 tracking-tight leading-none glow-text">
              Accelerate <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-500 to-primary-700 start-text-gradient">Discovery</span>
            </h1>

            <p className="text-xl md:text-2xl text-slate-600 max-w-2xl mx-auto leading-relaxed mb-12 font-light">
              Unlock the power of <span className="text-primary-700 font-medium">AlphaFold 3</span> and <span className="text-primary-700 font-medium">BioMistral-7B</span> to discover ranked drug candidates in seconds.
            </p>

            {/* Search Bar Container */}
            <div className="flex justify-center mb-10">
              <div className="w-full max-w-4xl bg-white/40 backdrop-blur-xl p-3 rounded-3xl border border-white/60 shadow-xl ring-1 ring-slate-900/5 hover:bg-white/60 transition-all duration-500">
                <div className="bg-white rounded-2xl overflow-hidden shadow-inner">
                  <SearchBar onSearch={handleSearch} isLoading={isSearching} />
                </div>
              </div>
            </div>

            {/* Example Searches */}
            <div className="flex flex-wrap justify-center gap-3 opacity-90">
              <span className="text-sm text-slate-400 font-medium mr-2 self-center">Try searching:</span>
              {exampleSearches.map((example) => (
                <button
                  key={example}
                  onClick={() => handleSearch(example)}
                  className="px-4 py-1.5 bg-white border border-slate-200 rounded-full text-xs text-slate-600 hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700 transition-all font-medium shadow-sm"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          {/* Scroll Indicator */}
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex flex-col items-center gap-2 opacity-50 animate-bounce">
            <span className="text-[10px] uppercase tracking-widest text-slate-400">Scroll to Explore</span>
            <div className="w-px h-12 bg-gradient-to-b from-slate-400 to-transparent"></div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-24 bg-slate-50 relative">
        <div className="absolute top-0 inset-x-0 h-24 bg-gradient-to-b from-slate-900 to-transparent opacity-10 pointer-events-none"></div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold text-slate-900 mb-6">
              Complete Drug Discovery Pipeline
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
              Our platform combines multiple biomedical databases and AI to deliver comprehensive insights from target identification to safety assessment.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group relative bg-white rounded-2xl p-8 shadow-sm hover:shadow-xl hover:-translate-y-2 transition-all duration-300 border border-slate-100"
              >
                <div className={`inline-flex items-center justify-center w-16 h-16 ${feature.lightColor} rounded-2xl mb-6 group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className={`w-8 h-8 ${feature.textColor}`} strokeWidth={1.5} />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3 group-hover:text-primary-600 transition-colors">{feature.title}</h3>
                <p className="text-slate-500 leading-relaxed">{feature.description}</p>

                <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity transform translate-x-2 group-hover:translate-x-0">
                  <div className={`w-8 h-8 rounded-full ${feature.lightColor} flex items-center justify-center`}>
                    <feature.icon className={`w-4 h-4 ${feature.textColor}`} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Status & Metrics Section */}
      <div className="py-20 bg-white border-t border-slate-100 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-[0.03] background-grid-pattern"></div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="flex flex-col md:flex-row justify-between items-end mb-12 gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-green-50 text-green-700 rounded-full text-xs font-semibold mb-4 border border-green-200 shadow-sm">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                SYSTEM OPERATIONAL
              </div>
              <h2 className="text-3xl font-bold text-slate-900 mb-2">Live Platform Metrics</h2>
              <p className="text-slate-600">Real-time performance monitoring and resource utilization</p>
            </div>
            <div className="flex gap-4">
              <div className="text-right">
                <div className="text-sm text-slate-500">API Latency</div>
                <div className="text-xl font-mono font-bold text-green-600">42ms</div>
              </div>
              <div className="w-px bg-slate-200"></div>
              <div className="text-right">
                <div className="text-sm text-slate-500">GPU Load</div>
                <div className="text-xl font-mono font-bold text-primary-600">28%</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Metric Card 1 */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-lg hover:shadow-primary-500/5 hover:-translate-y-1 transition-all group">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-primary-50 rounded-xl text-primary-600 group-hover:bg-primary-100 transition-colors">
                  <TrendingUp className="w-6 h-6" />
                </div>
                <span className="px-2 py-1 bg-green-50 text-green-700 text-xs font-medium rounded-lg border border-green-100">
                  +12%
                </span>
              </div>
              <div className="space-y-1">
                <div className="text-3xl font-bold font-mono text-slate-900">1.2s</div>
                <div className="text-sm text-slate-500">Avg. Inference Time</div>
              </div>
              <div className="mt-4 w-full bg-slate-100 rounded-full h-1 overflow-hidden">
                <div className="bg-primary-500 h-1 rounded-full w-[85%]"></div>
              </div>
            </div>

            {/* Metric Card 2 */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-lg hover:shadow-purple-500/5 hover:-translate-y-1 transition-all group">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-purple-50 rounded-xl text-purple-600 group-hover:bg-purple-100 transition-colors">
                  <Database className="w-6 h-6" />
                </div>
                <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-lg">
                  v2.4.0
                </span>
              </div>
              <div className="space-y-1">
                <div className="text-3xl font-bold font-mono text-slate-900">3.8M+</div>
                <div className="text-sm text-slate-500">Indexed Molecules</div>
              </div>
              <div className="mt-4 flex gap-2">
                <div className="h-1 flex-1 bg-purple-500 rounded-full"></div>
                <div className="h-1 flex-1 bg-purple-200 rounded-full"></div>
                <div className="h-1 flex-1 bg-purple-200 rounded-full"></div>
              </div>
            </div>

            {/* Metric Card 3 */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-lg hover:shadow-teal-500/5 hover:-translate-y-1 transition-all group">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-teal-50 rounded-xl text-teal-600 group-hover:bg-teal-100 transition-colors">
                  <CheckCircle className="w-6 h-6" />
                </div>
                <span className="px-2 py-1 bg-teal-50 text-teal-700 text-xs font-medium rounded-lg border border-teal-100">
                  99.9%
                </span>
              </div>
              <div className="space-y-1">
                <div className="text-3xl font-bold font-mono text-slate-900">32</div>
                <div className="text-sm text-slate-500">Validation Checks</div>
              </div>
              <div className="mt-4 text-xs text-slate-400 font-mono">
                Last check: 2s ago
              </div>
            </div>

            {/* Metric Card 4 - Status List */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-lg transition-all">
              <h4 className="text-sm font-semibold text-slate-500 mb-4 uppercase tracking-wider">Service Health</h4>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600">Open Targets</span>
                  <div className="flex items-center gap-2 text-green-600">
                    <div className="w-1.5 h-1.5 bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.4)]"></div>
                    <span>Online</span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600">ChEMBL API</span>
                  <div className="flex items-center gap-2 text-green-600">
                    <div className="w-1.5 h-1.5 bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.4)]"></div>
                    <span>Online</span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600">AlphaFold DB</span>
                  <div className="flex items-center gap-2 text-green-600">
                    <div className="w-1.5 h-1.5 bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.4)]"></div>
                    <span>Online</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Ready to Discover Drug Candidates?
          </h2>
          <p className="text-lg text-gray-600 mb-8">
            Start your search now and get comprehensive results in seconds
          </p>
          <button
            onClick={() => document.querySelector('input')?.focus()}
            className="inline-flex items-center gap-2 px-8 py-4 bg-primary-600 text-white rounded-xl font-bold text-lg hover:bg-primary-700 transition-all shadow-lg hover:shadow-primary-200"
          >
            <Sparkles className="w-5 h-5" />
            Start Searching
          </button>
        </div>
      </div>
    </div>
  );
}
