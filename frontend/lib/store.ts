import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { DiscoveryResponse, UIPreferences } from '@/types';

interface AppState {
  // Search state
  currentQuery: string;
  setCurrentQuery: (query: string) => void;

  // Results state
  discoveryResults: DiscoveryResponse | null;
  setDiscoveryResults: (results: DiscoveryResponse | null) => void;

  // UI preferences
  preferences: UIPreferences;
  setPreferences: (preferences: Partial<UIPreferences>) => void;

  // Reset
  reset: () => void;
}

const defaultPreferences: UIPreferences = {
  theme: 'light',
  disclaimerDismissed: false,
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentQuery: '',
      setCurrentQuery: (query) => set({ currentQuery: query }),

      discoveryResults: null,
      setDiscoveryResults: (results) => set({ discoveryResults: results }),

      preferences: defaultPreferences,
      setPreferences: (newPreferences) =>
        set((state) => ({
          preferences: { ...state.preferences, ...newPreferences },
        })),

      reset: () =>
        set({
          currentQuery: '',
          discoveryResults: null,
        }),
    }),
    {
      name: 'drug-discovery-storage',
      partialize: (state) => ({
        preferences: state.preferences,
      }),
    }
  )
);

export default useAppStore;
