// TypeScript types for SIGMA Agent Dashboard
// Generated from FastAPI Pydantic models in src/openmemory/app/routers/agents.py

export interface Project {
  project_id: number;
  repo_url: string;
  branch: string;
  language: string | null;
  framework: string | null;
  domain: string | null;
  created_at: string;
  last_analyzed: string | null;
}

export interface Proposal {
  proposal_id: number;
  project_id: number;
  title: string;
  description: string | null;
  confidence: number;
  critic_score: number;
  status: 'pending' | 'approved' | 'rejected' | 'executed';
  pr_url: string | null;
  commit_sha: string | null;
  created_at: string;
  executed_at: string | null;
}

export interface ProposalDetail extends Proposal {
  agents_json: string | null;
  changes_json: string | null;
}

export interface Experiment {
  experiment_id: number;
  worker_name: string;
  experiment_name: string;
  hypothesis: string | null;
  approach: string | null;
  success: boolean | null;
  improvement: number | null;
  promoted_to_production: boolean;
  created_at: string;
  completed_at: string | null;
}

export interface LearnedPattern {
  pattern_id: number;
  pattern_name: string;
  pattern_type: string;
  description: string | null;
  language: string;
  framework: string | null;
  domain: string | null;
  confidence: number;
  success_count: number;
  failure_count: number;
  created_at: string;
  last_used: string | null;
}

export interface WorkerStats {
  stat_id: number;
  worker_name: string;
  cycles_run: number;
  experiments_run: number;
  total_time: number;
  errors: number;
  last_run: string | null;
}

export interface DashboardStats {
  total_projects: number;
  active_proposals: number;
  pending_proposals: number;
  total_experiments: number;
  successful_experiments: number;
  promoted_experiments: number;
  total_patterns: number;
  worker_stats: WorkerStats[];
  recent_proposals: Proposal[];
  recent_experiments: Experiment[];
}

export interface CrossProjectOpportunity {
  learning_id: number;
  source_project: Project;
  target_project: Project;
  pattern: LearnedPattern;
  similarity_score: number;
  applied: boolean;
  created_at: string;
}

// API Request types
export interface ProjectCreateRequest {
  repo_url: string;
  branch?: string;
  workspace_path?: string;
  language: string;
  framework?: string;
  domain?: string;
  force_reclone?: boolean;
}

export interface ApprovalRequest {
  proposal_id: number;
  approved: boolean;
  comment?: string;
}

export interface WorkerStartRequest {
  worker_type: 'analysis' | 'dream' | 'recall' | 'learning' | 'think';
  project_id: number;
  max_iterations: number;
  dream_probability: number;
}

export interface WorkerStartResponse {
  success: boolean;
  worker_id: string;
  worker_type: string;
  message: string;
  status: string;
}

// Graph visualization types
export interface GraphNode {
  id: string;
  type: 'project' | 'pattern';
  label: string;
  data: {
    project_id?: number;
    repo_url?: string;
    language?: string;
    framework?: string;
    domain?: string;
    pattern_id?: number;
    pattern_type?: string;
    confidence?: number;
    success_count?: number;
    failure_count?: number;
  };
}

export interface GraphEdge {
  source: string;
  target: string;
  type: 'generates' | 'applies_to' | 'opportunity';
  data: {
    confidence?: number;
    similarity_score?: number;
    applied?: boolean;
    created_at?: string;
  };
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: {
    total_projects: number;
    total_patterns: number;
    total_connections: number;
    timestamp: string;
  };
}

// Worker log types
export interface WorkerLog {
  timestamp: string;
  worker: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  metadata?: Record<string, any>;
}

// Toast notification types
export interface Toast {
  id: number;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

// Tab type
export type TabName = 'proposals' | 'experiments' | 'workers' | 'patterns' | 'projects' | 'logs' | 'graph';
