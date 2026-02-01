import { useState } from 'react';
import { FileText, ThumbsUp, ThumbsDown, ExternalLink } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useDashboard } from '@/hooks/useDashboard';
import type { Proposal } from '@/types';
import { format } from 'date-fns';

export function ProposalsTab() {
  const { proposals, approveProposal, addToast } = useDashboard();
  const [approvalDialog, setApprovalDialog] = useState<{
    proposal: Proposal;
    approved: boolean;
  } | null>(null);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleApprovalAction = (proposal: Proposal, approved: boolean) => {
    setApprovalDialog({ proposal, approved });
    setComment('');
  };

  const handleSubmitApproval = async () => {
    if (!approvalDialog) return;

    setIsSubmitting(true);

    try {
      await approveProposal(
        approvalDialog.proposal.proposal_id,
        approvalDialog.approved,
        comment
      );

      addToast({
        message: `Proposal ${approvalDialog.approved ? 'approved' : 'rejected'} successfully`,
        type: 'success',
      });

      setApprovalDialog(null);
      setComment('');
    } catch (error) {
      console.error('Error updating proposal:', error);
      addToast({
        message: `Failed to ${approvalDialog.approved ? 'approve' : 'reject'} proposal: ${
          error instanceof Error ? error.message : 'Unknown error'
        }`,
        type: 'error',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getBadgeClass = (status: Proposal['status']): string => {
    switch (status) {
      case 'pending':
        return 'bg-terminal-yellow/20 text-terminal-yellow border-terminal-yellow/30';
      case 'approved':
        return 'bg-terminal-green/20 text-terminal-green border-terminal-green/30';
      case 'rejected':
        return 'bg-terminal-red/20 text-terminal-red border-terminal-red/30';
      case 'executed':
        return 'bg-terminal-blue/20 text-terminal-blue border-terminal-blue/30';
      default:
        return '';
    }
  };

  const formatConfidence = (value: number): string => {
    return `${(value * 100).toFixed(0)}%`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-primary flex items-center gap-2">
          <FileText className="h-6 w-6" />
          Code Improvement Proposals
        </h2>
        <div className="text-sm text-gray-500">
          {proposals.filter((p) => p.status === 'pending').length} pending
        </div>
      </div>

      {/* Approval/Rejection Dialog */}
      <Dialog open={!!approvalDialog} onOpenChange={() => setApprovalDialog(null)}>
        <DialogContent className="sm:max-w-[500px] bg-background-secondary border-primary/20">
          <DialogHeader>
            <DialogTitle className={`flex items-center gap-2 ${
              approvalDialog?.approved ? 'text-terminal-green' : 'text-terminal-red'
            }`}>
              {approvalDialog?.approved ? (
                <>
                  <ThumbsUp className="h-5 w-5" />
                  Approve Proposal
                </>
              ) : (
                <>
                  <ThumbsDown className="h-5 w-5" />
                  Reject Proposal
                </>
              )}
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              {approvalDialog?.approved
                ? 'This proposal will be marked as approved and can be executed.'
                : 'This proposal will be rejected and will not be executed.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="p-4 bg-background rounded-lg border border-gray-800">
              <h4 className="font-semibold text-primary mb-2">{approvalDialog?.proposal.title}</h4>
              <p className="text-sm text-gray-400">{approvalDialog?.proposal.description}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="comment" className="text-gray-300">
                Comment (Optional)
              </Label>
              <Textarea
                id="comment"
                placeholder="Add any notes or feedback..."
                value={comment}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setComment(e.target.value)}
                className="terminal-border bg-background min-h-[100px]"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setApprovalDialog(null)}
              disabled={isSubmitting}
              className="border-gray-600 text-gray-300 hover:bg-background-tertiary"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmitApproval}
              disabled={isSubmitting}
              className={
                approvalDialog?.approved
                  ? 'bg-terminal-green text-background hover:bg-terminal-green/90'
                  : 'bg-terminal-red text-white hover:bg-terminal-red/90'
              }
            >
              {isSubmitting
                ? 'Processing...'
                : approvalDialog?.approved
                ? 'Approve'
                : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Proposals List */}
      {proposals.length === 0 ? (
        <Card className="terminal-card p-12 text-center">
          <FileText className="h-16 w-16 mx-auto mb-4 text-gray-600" />
          <p className="text-gray-400 text-lg mb-2">No proposals found</p>
          <p className="text-gray-500 text-sm">
            Proposals will appear here after workers analyze your projects
          </p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {proposals.map((proposal: Proposal) => (
            <Card
              key={proposal.proposal_id}
              className="terminal-card p-6 hover:border-primary/50 transition-colors"
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold glow-text mb-2">
                      {proposal.title}
                    </h3>
                    <p className="text-gray-400 text-sm leading-relaxed">
                      {proposal.description || 'No description provided'}
                    </p>
                  </div>
                  <Badge className={getBadgeClass(proposal.status)}>
                    {proposal.status.toUpperCase()}
                  </Badge>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-4 p-4 bg-background rounded-lg border border-gray-800">
                  <div>
                    <div className="text-sm text-gray-500 mb-1">Confidence</div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-background-tertiary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-terminal-green transition-all"
                          style={{ width: `${proposal.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-mono text-terminal-green">
                        {formatConfidence(proposal.confidence)}
                      </span>
                    </div>
                  </div>

                  <div>
                    <div className="text-sm text-gray-500 mb-1">Critic Score</div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-background-tertiary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-terminal-yellow transition-all"
                          style={{ width: `${proposal.critic_score * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-mono text-terminal-yellow">
                        {formatConfidence(proposal.critic_score)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* PR Link */}
                {proposal.pr_url && (
                  <div className="flex items-center gap-2 text-sm">
                    <ExternalLink className="h-4 w-4 text-terminal-blue" />
                    <a
                      href={proposal.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-terminal-blue hover:underline font-mono"
                    >
                      {proposal.pr_url}
                    </a>
                  </div>
                )}

                {/* Timestamp */}
                <div className="flex items-center justify-between text-xs text-gray-600 font-mono">
                  <span>Created: {format(new Date(proposal.created_at), 'MMM d, yyyy HH:mm')}</span>
                  {proposal.executed_at && (
                    <span>Executed: {format(new Date(proposal.executed_at), 'MMM d, yyyy HH:mm')}</span>
                  )}
                </div>

                {/* Actions */}
                {proposal.status === 'pending' && (
                  <div className="flex gap-3 pt-2 border-t border-gray-800">
                    <Button
                      onClick={() => handleApprovalAction(proposal, true)}
                      className="flex-1 bg-terminal-green/20 text-terminal-green border border-terminal-green/30 hover:bg-terminal-green/30"
                    >
                      <ThumbsUp className="h-4 w-4 mr-2" />
                      Approve
                    </Button>
                    <Button
                      onClick={() => handleApprovalAction(proposal, false)}
                      variant="outline"
                      className="flex-1 border-terminal-red/50 text-terminal-red hover:bg-terminal-red/10"
                    >
                      <ThumbsDown className="h-4 w-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
