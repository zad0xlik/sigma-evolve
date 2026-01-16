// Project Registration Form Component
import { api } from '/static/js/api.js';
import { utils } from '/static/js/utils.js';

export function projectForm() {
    return {
        // Form state
        isOpen: true, // Open by default for better visibility
        isSubmitting: false,
        
        // Form data
        form: {
            repo_url: '',
            branch: 'main',
            language: '',
            framework: '',
            domain: ''
        },
        
        // Validation errors
        errors: {
            repo_url: '',
            language: ''
        },
        
        // Language options
        languages: [
            'Python',
            'JavaScript',
            'TypeScript',
            'Go',
            'Rust',
            'Java',
            'Ruby',
            'PHP',
            'C++',
            'C#'
        ],
        
        // Toggle form visibility
        toggle() {
            this.isOpen = !this.isOpen;
            if (this.isOpen) {
                // Reset form when opening
                this.resetForm();
            }
        },
        
        // Reset form
        resetForm() {
            this.form = {
                repo_url: '',
                branch: 'main',
                language: '',
                framework: '',
                domain: ''
            };
            this.errors = {
                repo_url: '',
                language: ''
            };
        },
        
        // Validate form
        validate() {
            let isValid = true;
            this.errors = {};
            
            // Validate repo URL
            if (!this.form.repo_url) {
                this.errors.repo_url = 'Repository URL is required';
                isValid = false;
            } else if (!utils.isValidGitHubUrl(this.form.repo_url)) {
                this.errors.repo_url = 'Please enter a valid GitHub URL';
                isValid = false;
            }
            
            // Validate language
            if (!this.form.language) {
                this.errors.language = 'Language is required';
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
                const result = await api.registerProject(this.form);
                
                if (result.project_id) {
                    utils.success(`Project registered successfully! ID: ${result.project_id}`);
                    this.isOpen = false;
                    this.resetForm();
                    
                    // Trigger refresh of projects list
                    window.dispatchEvent(new CustomEvent('project-registered'));
                    
                    // Optionally prompt to start analysis
                    setTimeout(() => {
                        if (confirm('Would you like to start analysis on this project?')) {
                            // Switch to workers tab and open worker form
                            window.dispatchEvent(new CustomEvent('start-analysis', {
                                detail: { projectId: result.project_id }
                            }));
                        }
                    }, 500);
                } else {
                    utils.error('Failed to register project');
                }
            } catch (error) {
                console.error('Error registering project:', error);
                utils.error('Failed to register project: ' + error.message);
            } finally {
                this.isSubmitting = false;
            }
        },
        
        // Extract repo name from URL
        getRepoName() {
            if (!this.form.repo_url) return '';
            try {
                const url = new URL(this.form.repo_url);
                const parts = url.pathname.split('/').filter(p => p);
                if (parts.length >= 2) {
                    return `${parts[0]}/${parts[1].replace('.git', '')}`;
                }
            } catch (e) {
                return '';
            }
            return '';
        }
    };
}

// Register globally for Alpine
window.projectForm = projectForm;
