// API Layer - All backend communication
const API_BASE = window.location.origin;

export const api = {
    // Dashboard stats
    async getDashboard() {
        const response = await fetch(`${API_BASE}/api/agents/dashboard`);
        if (!response.ok) throw new Error('Failed to fetch dashboard');
        return response.json();
    },

    // Proposals
    async getProposals(limit = 20) {
        const response = await fetch(`${API_BASE}/api/agents/proposals?limit=${limit}`);
        if (!response.ok) throw new Error('Failed to fetch proposals');
        return response.json();
    },

    async getProposal(id) {
        const response = await fetch(`${API_BASE}/api/agents/proposals/${id}`);
        if (!response.ok) throw new Error('Failed to fetch proposal');
        return response.json();
    },

    async approveProposal(proposalId, approved, comment = '') {
        const response = await fetch(`${API_BASE}/api/agents/proposals/${proposalId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                proposal_id: proposalId,
                approved,
                comment: comment || (approved ? 'Approved via dashboard' : 'Rejected via dashboard')
            })
        });
        if (!response.ok) throw new Error('Failed to approve proposal');
        return response.json();
    },

    // Experiments
    async getExperiments(limit = 20) {
        const response = await fetch(`${API_BASE}/api/agents/experiments?limit=${limit}`);
        if (!response.ok) throw new Error('Failed to fetch experiments');
        return response.json();
    },

    // Workers
    async getWorkerStats() {
        const response = await fetch(`${API_BASE}/api/agents/workers/stats`);
        if (!response.ok) throw new Error('Failed to fetch worker stats');
        return response.json();
    },

    async startWorker(data) {
        const response = await fetch(`${API_BASE}/api/agents/workers/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to start worker');
        return response.json();
    },

    // Patterns
    async getPatterns(limit = 20) {
        const response = await fetch(`${API_BASE}/api/agents/patterns?limit=${limit}`);
        if (!response.ok) throw new Error('Failed to fetch patterns');
        return response.json();
    },

    // Projects
    async getProjects(limit = 20) {
        const response = await fetch(`${API_BASE}/api/agents/projects?limit=${limit}`);
        if (!response.ok) throw new Error('Failed to fetch projects');
        return response.json();
    },

    async registerProject(data) {
        const response = await fetch(`${API_BASE}/api/agents/projects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to register project');
        return response.json();
    },

    async deleteProject(projectId) {
        const response = await fetch(`${API_BASE}/api/agents/projects/${projectId}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Failed to delete project');
        return response.json();
    },

    // Graph visualization
    async getProjectPatternGraph() {
        const response = await fetch(`${API_BASE}/api/agents/graph/project-patterns`);
        if (!response.ok) throw new Error('Failed to fetch graph data');
        return response.json();
    }
};
