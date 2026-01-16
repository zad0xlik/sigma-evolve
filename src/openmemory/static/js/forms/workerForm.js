// Worker Control Form Component
import { api } from '/static/js/api.js';
import { utils } from '/static/js/utils.js';

export function workerForm() {
    return {
        // Form state
        isOpen: true, // Open by default for better visibility
        isSubmitting: false,
        showAdvanced: false,
        
        // Form data
        form: {
            worker_type: '',
            project_id: null,
            max_iterations: 5,
            dream_probability: 0.15
        },
        
        // Validation errors
        errors: {},
        
        // Worker types
        workerTypes: [
            { value: 'analysis', label: 'Analysis Worker', description: 'Code parsing, metrics, issue detection' },
            { value: 'dream', label: 'Dream Worker', description: 'Knowledge graph relationships' },
            { value: 'recall', label: 'Recall Worker', description: 'Semantic search & indexing' },
            { value: 'learning', label: 'Learning Worker', description: 'Pattern transfer, meta-learning' },
            { value: 'think', label: 'Think Worker', description: 'Multi-agent committee decisions' }
        ],
        
        // Projects (loaded from parent)
        get projects() {
            return this.$root.projects || [];
        },
        
        // Init
        init() {
            // Listen for start-analysis event
            window.addEventListener('start-analysis', (e) => {
                this.form.worker_type = 'analysis';
                this.form.project_id = e.detail.projectId;
                this.isOpen = true;
                
                // Switch to workers tab
                this.$root.switchTab('workers');
            });
        },
        
        // Toggle form visibility
        toggle() {
            this.isOpen = !this.isOpen;
            if (this.isOpen) {
                this.resetErrors();
            }
        },
        
        // Reset errors
        resetErrors() {
            this.errors = {};
        },
        
        // Validate form
        validate() {
            let isValid = true;
            this.errors = {};
            
            if (!this.form.worker_type) {
                this.errors.worker_type = 'Worker type is required';
                isValid = false;
            }
            
            if (!this.form.project_id) {
                this.errors.project_id = 'Project is required';
                isValid = false;
            }
            
            if (this.form.max_iterations < 1 || this.form.max_iterations > 100) {
                this.errors.max_iterations = 'Max iterations must be between 1 and 100';
                isValid = false;
            }
            
            if (this.form.dream_probability < 0 || this.form.dream_probability > 1) {
                this.errors.dream_probability = 'Dream probability must be between 0 and 1';
                isValid = false;
            }
            
            return isValid;
        },
        
        // Submit form
        async submit() {
            if (!this.validate()) {
                return;
            }
            
            this.isSubmitting = true;
            
            try {
                const result = await api.startWorker(this.form);
                
                if (result.success || result.worker_id) {
                    utils.success(`${this.getWorkerLabel()} started successfully!`);
                    this.isOpen = false;
                    
                    // Refresh workers list
                    await this.$root.loadTabData();
                } else {
                    utils.error('Failed to start worker: ' + (result.message || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error starting worker:', error);
                utils.error('Failed to start worker: ' + error.message);
            } finally {
                this.isSubmitting = false;
            }
        },
        
        // Get worker label
        getWorkerLabel() {
            const worker = this.workerTypes.find(w => w.value === this.form.worker_type);
            return worker ? worker.label : 'Worker';
        },
        
        // Get worker description
        getWorkerDescription() {
            const worker = this.workerTypes.find(w => w.value === this.form.worker_type);
            return worker ? worker.description : '';
        },
        
        // Get project name
        getProjectName(projectId) {
            const project = this.projects.find(p => p.project_id === projectId);
            if (!project) return 'Unknown';
            
            try {
                const url = new URL(project.repo_url);
                const parts = url.pathname.split('/').filter(p => p);
                if (parts.length >= 2) {
                    return `${parts[0]}/${parts[1].replace('.git', '')}`;
                }
            } catch (e) {
                return project.repo_url;
            }
            
            return project.repo_url;
        },
        
        // Format dream probability percentage
        get dreamProbabilityPercent() {
            return Math.round(this.form.dream_probability * 100);
        }
    };
}

// Register globally for Alpine
window.workerForm = workerForm;
