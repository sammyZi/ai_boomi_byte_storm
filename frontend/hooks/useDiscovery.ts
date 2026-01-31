import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import DiscoveryAPI from '@/lib/discovery-api';
import { DiscoveryResponse, ErrorResponse } from '@/types';

export function useDiscovery(diseaseName?: string) {
  const queryClient = useQueryClient();

  // Query for fetching discovery results
  const query = useQuery<DiscoveryResponse, ErrorResponse>({
    queryKey: ['discovery', diseaseName],
    queryFn: () => DiscoveryAPI.discoverDrugs(diseaseName!),
    enabled: !!diseaseName && diseaseName.length >= 2,
    staleTime: 1000 * 60 * 60, // 1 hour
    gcTime: 1000 * 60 * 60 * 24, // 24 hours (formerly cacheTime)
    retry: 1,
  });

  // Mutation for triggering new searches
  const mutation = useMutation<DiscoveryResponse, ErrorResponse, string>({
    mutationFn: (disease: string) => DiscoveryAPI.discoverDrugs(disease),
    onSuccess: (data, variables) => {
      // Update the query cache with the new data
      queryClient.setQueryData(['discovery', variables], data);
    },
  });

  return {
    // Query state
    data: query.data,
    isLoading: query.isLoading || mutation.isPending,
    isError: query.isError || mutation.isError,
    error: query.error || mutation.error,
    isSuccess: query.isSuccess || mutation.isSuccess,

    // Mutation methods
    search: mutation.mutate,
    searchAsync: mutation.mutateAsync,

    // Refetch method
    refetch: query.refetch,

    // Reset method
    reset: () => {
      query.remove();
      mutation.reset();
    },
  };
}

export default useDiscovery;
