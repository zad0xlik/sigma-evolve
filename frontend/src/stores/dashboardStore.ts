// Zustand Dashboard Store
// Global state management for SIGMA Agent Dashboard

import { create } from 'zustand';
import type {
  TabName,
  Proposal,
  Experiment,
  WorkerStats,
  LearnedPattern,
  Project,
  Toast,
  ProjectCreateRequest,
  WorkerStartRequest,
} from '@/types';
import { api } from '@/lib/api';

interface DashboardState {
  // Current UI state
  currentTab: TabName;
  loading: boolean;
  lastUpdate: string | null;
  autoRefresh: boolean;
  
  // Dashboard data
  stats: {
    totalProjects: number;
    pendingProposals: number;
    successRate: string;
    totalPatterns: number;
  };
  proposals: Proposal[];
  experiments: Experiment[];
  workers: WorkerStats[];
  patterns: LearnedPattern[];
  projects: Project[];
  
  // Toast notifications
  toasts: Toast[];
  
  // Actions
  setTab: (tab: TabName) => void;
  setLoading: (loading: boolean) => void;
  setAutoRefresh: (enabled: boolean) => void;
  
  // Data loading
  refreshData: () => Promise<void>;
  loadStats: () => Promise<void>;
  loadTabData: () => Promise<void>;
  
  // Toast management
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: number) => void;
  
  // Proposal actions
  approveProposal: (proposalId: number, approved: boolean, comment?: string) => Promise<void>;
  
  // Project actions
  registerProject: (data: ProjectCreateRequest) => Promise<Project>;
  deleteProject: (projectId: number) => Promise<void>;
  
  // Worker actions
  startWorker: (data: WorkerStartRequest) => Promise<void>;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  // Initial state
  currentTab: (localStorage.getItem('currentTab') as TabName) || 'proposals',
  loading: false,
  lastUpdate: null,
  autoRefresh: true,
  
  stats: {
    totalProjects: 0,
    pendingProposals: 0,
    successRate: '0%',
    totalPatterns: 0,
  },
  proposals: [],
  experiments: [],
  workers: [],
  patterns: [],
  projects: [],
  toasts: [],
  
  // Set current tab
  setTab: (tab: TabName) => {
    set({ currentTab: tab });
    localStorage.setItem('currentTab', tab);
    get().loadTabData();
  },
  
  // Set loading state
  setLoading: (loading: boolean) => {
    set({ loading });
  },
  
  // Toggle auto-refresh
  setAutoRefresh: (enabled: boolean) => {
    set({ autoRefresh: enabled });
    get().addToast({
      message: `Auto-refresh ${enabled ? 'enabled' : 'disabled'}`,
      type: 'info',
    });
  },
  
  // Refresh all data
  refreshData: async () => {
    set({ loading: true });
    try {
      await get().loadStats();
      await get().loadTabData();
      set({ lastUpdate: new Date().toLocaleString() });
    } catch (error) {
      console.error('Error refreshing data:', error);
      get().addToast({ message: 'Failed to refresh data', type: 'error' });
    } finally {
      set({ loading: false });
    }
  },
  
  // Load dashboard stats
  loadStats: async () => {
    try {
      const data = await api.getDashboard();
      
      const successRate =
        data.total_experiments > 0
          ? Math.round((data.successful_experiments / data.total_experiments) * 100)
          : 0;
      
      set({
        stats: {
          totalProjects: data.total_projects,
          pendingProposals: data.pending_proposals,
          successRate: `${successRate}%`,
          totalPatterns: data.total_patterns,
        },
        workers: data.worker_stats,
      });
      
      // Always load projects so worker form has them available
      if (get().projects.length === 0) {
        const projects = await api.getProjects();
        set({ projects });
      }
    } catch (error) {
      console.error('Error loading stats:', error);
      get().addToast({ message: 'Failed to load stats', type: 'error' });
    }
  },
  
  // Load current tab data
  loadTabData: async () => {
    const { currentTab } = get();
    
    try {
      switch (currentTab) {
        case 'proposals': {
          const proposals = await api.getProposals();
          set({ proposals });
          break;
        }
        case 'experiments': {
          const experiments = await api.getExperiments();
          set({ experiments });
          break;
        }
        case 'workers': {
          const workers = await api.getWorkerStats();
          set({ workers });
          // Ensure projects are loaded for worker form dropdown
          if (get().projects.length === 0) {
            const projects = await api.getProjects();
            set({ projects });
          }
          break;
        }
        case 'patterns': {
          const patterns = await api.getPatterns();
          set({ patterns });
          break;
        }
        case 'projects': {
          const projects = await api.getProjects();
          set({ projects });
          break;
        }
        case 'graph':
        case 'logs':
          // These tabs load their own data via components
          break;
      }
    } catch (error) {
      console.error(`Error loading ${currentTab}:`, error);
      get().addToast({ message: `Failed to load ${currentTab}`, type: 'error' });
    }
  },
  
  // Add toast notification
  addToast: (toast: Omit<Toast, 'id'>) => {
    const id = Date.now();
    const newToast: Toast = { ...toast, id };
    
    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      get().removeToast(id);
    }, 5000);
  },
  
  // Remove toast
  removeToast: (id: number) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
  
  // Approve or reject a proposal
  approveProposal: async (
    proposalId: number,
    approved: boolean,
    comment: string = ''
  ) => {
    try {
      const result = await api.approveProposal(proposalId, approved, comment);
      
      if (result.success) {
        get().addToast({
          message: `Proposal ${approved ? 'approved' : 'rejected'} successfully`,
          type: 'success',
        });
        await get().loadTabData();
        await get().loadStats();
      } else {
        get().addToast({ message: 'Failed to update proposal', type: 'error' });
      }
    } catch (error) {
      console.error('Error approving proposal:', error);
      get().addToast({ message: 'Failed to update proposal', type: 'error' });
    }
  },
  
  // Register a new project
  registerProject: async (data: ProjectCreateRequest): Promise<Project> => {
    try {
      const result = await api.registerProject(data);
      
      // Add to local projects array
      set((state) => ({
        projects: [...state.projects, result],
      }));
      
      // Refresh stats
      await get().loadStats();
      
      return result;
    } catch (error) {
      console.error('Error registering project:', error);
      throw error;
    }
  },
  
  // Delete a project
  deleteProject: async (projectId: number) => {
    try {
      const result = await api.deleteProject(projectId);
      
      if (result.success) {
        // Remove from local array immediately for instant UI update
        set((state) => ({
          projects: state.projects.filter((p) => p.project_id !== projectId),
        }));
        
        await get().loadStats();
      } else {
        throw new Error('Failed to delete project');
      }
    } catch (error) {
      console.error('Error deleting project:', error);
      throw error;
    }
  },
  
  // Start a worker
  startWorker: async (data: WorkerStartRequest) => {
    try {
      const result = await api.startWorker(data);
      
      if (result.success || result.worker_id) {
        get().addToast({
          message: `${data.worker_type} worker started successfully`,
          type: 'success',
        });
        await get().loadTabData();
      } else {
        throw new Error(result.message || 'Failed to start worker');
      }
    } catch (error) {
      console.error('Error starting worker:', error);
      throw error;
    }
  },
}));
