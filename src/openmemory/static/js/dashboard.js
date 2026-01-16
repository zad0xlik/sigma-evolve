// Main Dashboard Alpine.js Component
import { api } from '/static/js/api.js';
import { utils } from '/static/js/utils.js';

export function dashboardApp() {
    return {
        // State
        currentTab: 'proposals',
        loading: false,
        lastUpdate: null,
        autoRefresh: true,
        refreshInterval: null,
        
        // Data
        stats: {
            totalProjects: '-',
            pendingProposals: '-',
            successRate: '-',
            totalPatterns: '-'
        },
        proposals: [],
        experiments: [],
        workers: [],
        patterns: [],
        projects: [],
        
        // Toast notifications
        toasts: [],
        
        // Init
        async init() {
            // Load saved tab from localStorage
            const savedTab = utils.retrieve('currentTab', 'proposals');
            this.currentTab = savedTab;
            
            // Listen for toast events
            window.addEventListener('show-toast', (e) => {
                this.addToast(e.detail.message, e.detail.type);
            });
            
            // Initial data load
            await this.refreshData();
            
            // Start auto-refresh
            if (this.autoRefresh) {
                this.startAutoRefresh();
            }
            
            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Cmd/Ctrl + R to refresh
                if ((e.metaKey || e.ctrlKey) && e.key === 'r') {
                    e.preventDefault();
                    this.refreshData();
                }
                
                // Cmd/Ctrl + 1-5 to switch tabs
                if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '5') {
                    e.preventDefault();
                    const tabs = ['proposals', 'experiments', 'workers', 'patterns', 'projects'];
                    this.switchTab(tabs[parseInt(e.key) - 1]);
                }
            });
        },
        
        // Switch tab
        switchTab(tabName) {
            this.currentTab = tabName;
            utils.store('currentTab', tabName);
            this.loadTabData();
        },
        
        // Refresh all data
        async refreshData() {
            this.loading = true;
            try {
                // Load dashboard stats
                await this.loadStats();
                
                // Load current tab data
                await this.loadTabData();
                
                this.lastUpdate = new Date().toLocaleString();
            } catch (error) {
                console.error('Error refreshing data:', error);
                utils.error('Failed to refresh data');
            } finally {
                this.loading = false;
            }
        },
        
        // Load dashboard stats
        async loadStats() {
            try {
                const data = await api.getDashboard();
                this.stats.totalProjects = data.total_projects;
                this.stats.pendingProposals = data.pending_proposals;
                
                const successRate = data.total_experiments > 0 
                    ? Math.round((data.successful_experiments / data.total_experiments) * 100)
                    : 0;
                this.stats.successRate = successRate + '%';
                this.stats.totalPatterns = data.total_patterns;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        },
        
        // Load current tab data
        async loadTabData() {
            try {
                switch(this.currentTab) {
                    case 'proposals':
                        this.proposals = await api.getProposals();
                        break;
                    case 'experiments':
                        this.experiments = await api.getExperiments();
                        break;
                    case 'workers':
                        this.workers = await api.getWorkerStats();
                        break;
                    case 'patterns':
                        this.patterns = await api.getPatterns();
                        break;
                    case 'projects':
                        this.projects = await api.getProjects();
                        break;
                }
            } catch (error) {
                console.error(`Error loading ${this.currentTab}:`, error);
            }
        },
        
        // Approve/reject proposal
        async handleProposalAction(proposalId, approved) {
            try {
                const result = await api.approveProposal(proposalId, approved);
                if (result.success) {
                    utils.success(`Proposal ${approved ? 'approved' : 'rejected'} successfully`);
                    await this.loadTabData();
                    await this.loadStats();
                } else {
                    utils.error('Failed to update proposal');
                }
            } catch (error) {
                console.error('Error approving proposal:', error);
                utils.error('Failed to update proposal');
            }
        },
        
        // View proposal details
        async viewProposal(proposalId) {
            try {
                const proposal = await api.getProposal(proposalId);
                // Create modal or alert with details
                const details = JSON.stringify(proposal, null, 2);
                alert(`Proposal Details:\n\n${details}`);
            } catch (error) {
                console.error('Error viewing proposal:', error);
                utils.error('Failed to load proposal details');
            }
        },
        
        // Auto-refresh
        startAutoRefresh() {
            this.refreshInterval = setInterval(() => {
                this.refreshData();
            }, 30000); // 30 seconds
        },
        
        stopAutoRefresh() {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
                this.refreshInterval = null;
            }
        },
        
        toggleAutoRefresh() {
            this.autoRefresh = !this.autoRefresh;
            if (this.autoRefresh) {
                this.startAutoRefresh();
                utils.info('Auto-refresh enabled');
            } else {
                this.stopAutoRefresh();
                utils.info('Auto-refresh disabled');
            }
        },
        
        // Toast notifications
        addToast(message, type = 'info') {
            const id = Date.now();
            this.toasts.push({ id, message, type });
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                this.removeToast(id);
            }, 5000);
        },
        
        removeToast(id) {
            this.toasts = this.toasts.filter(t => t.id !== id);
        },
        
        // Formatters (for use in Alpine templates)
        formatDate: utils.formatDate,
        formatConfidence: utils.formatConfidence,
        formatTime: utils.formatTime,
        
        // Get experiment card class
        getExperimentClass(exp) {
            if (exp.promoted_to_production) return 'experiment-promoted';
            if (exp.success) return 'experiment-success';
            if (exp.success === false) return 'experiment-failure';
            return '';
        },
        
        // Get health indicator class
        getHealthClass(worker) {
            if (worker.errors === 0) return 'health-healthy';
            if (worker.errors < 5) return 'health-warning';
            return 'health-error';
        },
        
        // Get badge class
        getBadgeClass(status) {
            return `badge-${status}`;
        }
    };
}

// Register Alpine component globally
window.dashboardApp = dashboardApp;
