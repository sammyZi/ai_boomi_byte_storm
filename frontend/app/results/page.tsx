'use client';

import { Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import useDiscovery from '@/hooks/useDiscovery';
import LoadingIndicator from '@/components/LoadingIndicator';
import ErrorMessage from '@/components/ErrorMessage';
import EmptyState from '@/components/EmptyState';
import ResultsHeader from '@/components/ResultsHeader';
import CandidateList from '@/components/CandidateList';

function ResultsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const query = searchParams.get('q') || '';

  const { data, isLoading, isError, error, refetch } = useDiscovery(query);

  const handleSearchAgain = () => {
    router.push('/');
  };

  const handleRetry = () => {
    if (query) {
      refetch();
    }
  };

  if (!query || query.length < 2) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <ErrorMessage
          error={{
            error_code: 'INVALID_QUERY',
            message: 'Please provide a valid disease name (2-200 characters)',
            timestamp: new Date().toISOString(),
          }}
          onRetry={handleSearchAgain}
        />
      </div>
    );
  }

  if (isLoading) {
    console.log('Loading results for:', query);
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <LoadingIndicator message={`Discovering drug candidates for "${query}"...`} />
      </div>
    );
  }

  if (isError && error) {
    console.error('Error fetching results:', error);
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <ErrorMessage error={error} onRetry={handleRetry} />
      </div>
    );
  }

  if (!data || !data.candidates || data.candidates.length === 0) {
    // Log for debugging
    console.log('No candidates found. Data:', data);
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <EmptyState onSearchAgain={handleSearchAgain} />
      </div>
    );
  }

  console.log('Displaying results:', data.candidates.length, 'candidates');
  return (
    <div className="min-h-screen bg-gray-50 mt-8">
      <ResultsHeader data={data} />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <CandidateList candidates={data.candidates} />
      </div>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <LoadingIndicator />
        </div>
      }
    >
      <ResultsContent />
    </Suspense>
  );
}
