// Custom hooks for dashboard functionality
// Provides easy access to Zustand store and common patterns

import { useEffect } from 'react';
import { useDashboardStore } from '@/stores/dashboardStore';

/**
 * Hook to get dashboard store state and actions
 */
export function useDashboard() {
  return useDashboardStore();
}

/**
 * Hook to initialize dashboard data on mount
 * Call this in your main App component
 */
export function useDashboardInit() {
  const { refreshData, autoRefresh } = useDashboardStore();

  useEffect(() => {
    // Load initial data
    refreshData();

    // Setup auto-refresh interval if enabled
    let intervalId: number | null = null;

    if (autoRefresh) {
      intervalId = setInterval(() => {
        refreshData();
      }, 30000); // 30 seconds
    }

    // Cleanup on unmount
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [autoRefresh, refreshData]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + R to refresh
      if ((e.metaKey || e.ctrlKey) && e.key === 'r') {
        e.preventDefault();
        refreshData();
      }

      // Cmd/Ctrl + 1-7 to switch tabs
      if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '7') {
        e.preventDefault();
        const tabs = ['proposals', 'experiments', 'workers', 'patterns', 'projects', 'logs', 'graph'];
        const tabIndex = parseInt(e.key) - 1;
        if (tabs[tabIndex]) {
          useDashboardStore.getState().setTab(tabs[tabIndex] as any);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [refreshData]);
}

/**
 * Hook to get only the stats
 */
export function useDashboardStats() {
  return useDashboardStore((state) => state.stats);
}

/**
 * Hook to get only the current tab
 */
export function useCurrentTab() {
  return useDashboardStore((state) => state.currentTab);
}

/**
 * Hook to get only the loading state
 */
export function useLoading() {
  return useDashboardStore((state) => state.loading);
}

/**
 * Hook to get tab-specific data
 */
export function useTabData<T extends keyof ReturnType<typeof useDashboardStore>>(
  tabName: T
) {
  return useDashboardStore((state) => state[tabName]);
}

/**
 * Hook to get toast notifications
 */
export function useToasts() {
  return useDashboardStore((state) => state.toasts);
}
