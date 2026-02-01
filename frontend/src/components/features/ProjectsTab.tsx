import { useState } from 'react';
import { FolderGit2, Trash2, Plus } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDashboard } from '@/hooks/useDashboard';
import type { Project, ProjectCreateRequest } from '@/types';
import { format } from 'date-fns';

const LANGUAGES = [
  'Python',
  'JavaScript',
  'TypeScript',
  'Go',
  'Rust',
  'Java',
  'Ruby',
  'PHP',
  'C++',
  'C#',
];

export function ProjectsTab() {
  const { projects, registerProject, deleteProject, addToast } = useDashboard();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; name: string } | null>(null);

  const [formData, setFormData] = useState<ProjectCreateRequest>({
    repo_url: '',
    branch: 'main',
    language: '',
    framework: '',
    domain: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateGitHubUrl = (url: string): boolean => {
    try {
      const parsed = new URL(url);
      return parsed.hostname === 'github.com' && parsed.pathname.split('/').filter(Boolean).length >= 2;
    } catch {
      return false;
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.repo_url) {
      newErrors.repo_url = 'Repository URL is required';
    } else if (!validateGitHubUrl(formData.repo_url)) {
      newErrors.repo_url = 'Please enter a valid GitHub URL';
    }

    if (!formData.language) {
      newErrors.language = 'Language is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await registerProject(formData);

      if (result.project_id) {
        addToast({
          message: `Project registered successfully! ID: ${result.project_id}`,
          type: 'success',
        });

        // Reset form and close dialog
        setFormData({
          repo_url: '',
          branch: 'main',
          language: '',
          framework: '',
          domain: '',
        });
        setErrors({});
        setIsFormOpen(false);

        // Ask if user wants to start analysis
        setTimeout(() => {
          if (window.confirm('Would you like to start analysis on this project?')) {
            // This would trigger switching to workers tab and opening worker form
            // For now, just show a toast
            addToast({
              message: 'Go to Workers tab to start analysis',
              type: 'info',
            });
          }
        }, 500);
      }
    } catch (error) {
      console.error('Error registering project:', error);
      addToast({
        message: `Failed to register project: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'error',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;

    try {
      await deleteProject(deleteConfirm.id);
      addToast({
        message: 'Project deleted successfully',
        type: 'success',
      });
      setDeleteConfirm(null);
    } catch (error) {
      console.error('Error deleting project:', error);
      addToast({
        message: `Failed to delete project: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'error',
      });
    }
  };

  const getRepoName = (repoUrl: string): string => {
    try {
      const url = new URL(repoUrl);
      const parts = url.pathname.split('/').filter(Boolean);
      if (parts.length >= 2) {
        return `${parts[0]}/${parts[1].replace('.git', '')}`;
      }
    } catch {
      return repoUrl;
    }
    return repoUrl;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-primary flex items-center gap-2">
          <FolderGit2 className="h-6 w-6" />
          Tracked Projects
        </h2>
        <Button onClick={() => setIsFormOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Register New Project
        </Button>
      </div>

      {/* Registration Form Dialog */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="sm:max-w-[600px] bg-background-secondary border-primary/20">
          <DialogHeader>
            <DialogTitle className="text-primary flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Register New Project
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              Add a new GitHub repository to track and analyze
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Repository URL */}
            <div className="space-y-2">
              <Label htmlFor="repo_url" className="text-gray-300">
                Repository URL <span className="text-terminal-red">*</span>
              </Label>
              <Input
                id="repo_url"
                placeholder="https://github.com/username/repo"
                value={formData.repo_url}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, repo_url: e.target.value })}
                className={`terminal-border bg-background ${errors.repo_url ? 'border-terminal-red' : ''}`}
              />
              {errors.repo_url && (
                <p className="text-sm text-terminal-red">{errors.repo_url}</p>
              )}
              <p className="text-sm text-gray-500">
                GitHub repository URL (e.g., https://github.com/zad0xlik/kgdreaminvest)
              </p>
            </div>

            {/* Branch */}
            <div className="space-y-2">
              <Label htmlFor="branch" className="text-gray-300">Branch</Label>
              <Input
                id="branch"
                placeholder="main"
                value={formData.branch}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, branch: e.target.value })}
                className="terminal-border bg-background"
              />
              <p className="text-sm text-gray-500">Git branch to analyze (default: main)</p>
            </div>

            {/* Language */}
            <div className="space-y-2">
              <Label htmlFor="language" className="text-gray-300">
                Language <span className="text-terminal-red">*</span>
              </Label>
              <Select
                value={formData.language}
                onValueChange={(value: string) => setFormData({ ...formData, language: value })}
              >
                <SelectTrigger className={`terminal-border bg-background ${errors.language ? 'border-terminal-red' : ''}`}>
                  <SelectValue placeholder="Select language..." />
                </SelectTrigger>
                <SelectContent className="bg-background-secondary border-primary/20">
                  {LANGUAGES.map((lang) => (
                    <SelectItem key={lang} value={lang} className="text-gray-300 focus:bg-background-tertiary focus:text-primary">
                      {lang}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.language && (
                <p className="text-sm text-terminal-red">{errors.language}</p>
              )}
            </div>

            {/* Framework */}
            <div className="space-y-2">
              <Label htmlFor="framework" className="text-gray-300">Framework (Optional)</Label>
              <Input
                id="framework"
                placeholder="e.g., fastapi, react, express"
                value={formData.framework}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, framework: e.target.value })}
                className="terminal-border bg-background"
              />
              <p className="text-sm text-gray-500">Framework used in the project</p>
            </div>

            {/* Domain */}
            <div className="space-y-2">
              <Label htmlFor="domain" className="text-gray-300">Domain (Optional)</Label>
              <Input
                id="domain"
                placeholder="e.g., investment-research, web-app"
                value={formData.domain}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, domain: e.target.value })}
                className="terminal-border bg-background"
              />
              <p className="text-sm text-gray-500">Project domain or category</p>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsFormOpen(false)}
                className="border-gray-600 text-gray-300 hover:bg-background-tertiary"
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting} className="bg-primary text-background hover:bg-primary/90">
                {isSubmitting ? 'Registering...' : 'Register Project'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent className="sm:max-w-[425px] bg-background-secondary border-terminal-red/50">
          <DialogHeader>
            <DialogTitle className="text-terminal-red flex items-center gap-2">
              <Trash2 className="h-5 w-5" />
              Delete Project
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              Are you sure you want to delete <span className="text-primary font-semibold">{deleteConfirm?.name}</span>?
              <br />
              <br />
              This will permanently delete the project and all related data (proposals, experiments, patterns).
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteConfirm(null)}
              className="border-gray-600 text-gray-300 hover:bg-background-tertiary"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDelete}
              className="bg-terminal-red text-white hover:bg-terminal-red/90"
            >
              Delete Project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Projects List */}
      {projects.length === 0 ? (
        <Card className="terminal-card p-12 text-center">
          <FolderGit2 className="h-16 w-16 mx-auto mb-4 text-gray-600" />
          <p className="text-gray-400 text-lg mb-2">No projects found</p>
          <p className="text-gray-500 text-sm">Register a project to get started with analysis</p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {projects.map((project: Project) => (
            <Card key={project.project_id} className="terminal-card p-6 hover:border-primary/50 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-3">
                  <div>
                    <h3 className="text-xl font-mono glow-text mb-1">
                      {getRepoName(project.repo_url)}
                    </h3>
                    <p className="text-sm text-gray-500 font-mono">{project.repo_url}</p>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Branch:</span>
                      <span className="ml-2 text-terminal-blue font-mono">{project.branch}</span>
                    </div>
                    {project.language && (
                      <div>
                        <span className="text-gray-500">Language:</span>
                        <span className="ml-2 text-terminal-green font-mono">{project.language}</span>
                      </div>
                    )}
                    {project.framework && (
                      <div>
                        <span className="text-gray-500">Framework:</span>
                        <span className="ml-2 text-terminal-purple font-mono">{project.framework}</span>
                      </div>
                    )}
                    {project.domain && (
                      <div>
                        <span className="text-gray-500">Domain:</span>
                        <span className="ml-2 text-terminal-yellow font-mono">{project.domain}</span>
                      </div>
                    )}
                  </div>

                  <div className="text-xs text-gray-600 font-mono">
                    Created: {format(new Date(project.created_at), 'MMM d, yyyy HH:mm')}
                    {project.last_analyzed && (
                      <span className="ml-4">
                        Last analyzed: {format(new Date(project.last_analyzed), 'MMM d, yyyy HH:mm')}
                      </span>
                    )}
                  </div>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setDeleteConfirm({ id: project.project_id, name: getRepoName(project.repo_url) })}
                  className="border-terminal-red/50 text-terminal-red hover:bg-terminal-red/10 hover:border-terminal-red ml-4"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
