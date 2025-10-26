import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Calendar, 
  Clock, 
  Send, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Video,
  Users
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import { Clip } from "@/hooks/useClips";

interface SocialAccount {
  id: string;
  platform: string;
  account_id: string;
  account_name: string;
  is_active: boolean;
}

interface PostSchedulerModalProps {
  clip: Clip;
  isOpen: boolean;
  onClose: () => void;
}

const PostSchedulerModal: React.FC<PostSchedulerModalProps> = ({
  clip,
  isOpen,
  onClose
}) => {
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [caption, setCaption] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [isImmediate, setIsImmediate] = useState(true);
  const queryClient = useQueryClient();

  // Fetch social accounts
  const { data: accounts, isLoading: accountsLoading } = useQuery({
    queryKey: ["social-accounts"],
    queryFn: async () => {
      const response = await apiClient.getSocialAccounts();
      return response.accounts as SocialAccount[];
    },
    enabled: isOpen,
  });

  // Schedule post mutation
  const schedulePost = useMutation({
    mutationFn: async (data: {
      clip_id: string;
      account_ids: string[];
      scheduled_at?: string;
      caption?: string;
    }) => {
      return await apiClient.schedulePost(data.clip_id, data.account_ids, data.scheduled_at, data.caption);
    },
    onSuccess: (data) => {
      toast.success(
        data.immediate 
          ? `🚀 Posting to ${data.queue_items.length} account(s) now...`
          : `📅 Post scheduled for ${data.queue_items.length} account(s)`,
        {
          description: data.immediate 
            ? "Your clips are being uploaded to social media. You'll get a notification when they're posted!"
            : "Your clips will be posted at the scheduled time.",
          duration: 6000,
        }
      );
      queryClient.invalidateQueries({ queryKey: ["posting-queue"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      onClose();
    },
    onError: (error: any) => {
      toast.error(`Failed to schedule post: ${error.message}`);
    },
  });

  // Reset form when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setSelectedAccounts([]);
      setCaption("");
      setScheduledAt("");
      setIsImmediate(true);
    }
  }, [isOpen]);

  const handleAccountToggle = (accountId: string) => {
    setSelectedAccounts(prev => 
      prev.includes(accountId) 
        ? prev.filter(id => id !== accountId)
        : [...prev, accountId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (selectedAccounts.length === 0) {
      toast.error("Please select at least one account");
      return;
    }

    const postData = {
      clip_id: clip.id,
      account_ids: selectedAccounts,
      caption: caption.trim() || undefined,
      scheduled_at: isImmediate ? undefined : scheduledAt,
    };

    await schedulePost.mutateAsync(postData);
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'tiktok':
        return '🎵';
      case 'youtube':
        return '📺';
      default:
        return '🔗';
    }
  };

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'tiktok':
        return 'bg-pink-500';
      case 'youtube':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const formatDateTime = (dateTime: string) => {
    return new Date(dateTime).toLocaleString();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent 
        className="max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Video className="w-5 h-5" />
            Post to Social Media
          </DialogTitle>
          <DialogDescription>
            Schedule this clip to be posted to your connected social media accounts
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Clip Preview */}
          <div className="space-y-2">
            <Label>Clip Preview</Label>
            <div className="p-4 rounded-lg border bg-muted/20">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Video className="w-6 h-6 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="font-medium truncate">{clip.channel_name}</div>
                  <div className="text-sm text-muted-foreground">
                    {clip.confidence_score ? `Score: ${clip.confidence_score.toFixed(2)}` : 'No score available'}
                  </div>
                </div>
                <Badge variant="outline">
                  {clip.file_size ? `${(clip.file_size / 1024 / 1024).toFixed(1)}MB` : 'Unknown size'}
                </Badge>
              </div>
            </div>
          </div>

          {/* Account Selection */}
          <div className="space-y-3">
            <Label>Select Accounts</Label>
            {accountsLoading ? (
              <div className="text-center py-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2"></div>
                <p className="text-sm text-muted-foreground">Loading accounts...</p>
              </div>
            ) : accounts && accounts.length > 0 ? (
              <div className="space-y-2">
                {accounts.map((account) => (
                  <div
                    key={account.id}
                    className="flex items-center space-x-3 p-3 rounded-lg border hover:bg-muted/20"
                  >
                    <Checkbox
                      id={account.id}
                      checked={selectedAccounts.includes(account.id)}
                      onCheckedChange={() => handleAccountToggle(account.id)}
                    />
                    <div className="flex items-center gap-3 flex-1">
                      <div className={`w-8 h-8 rounded-lg ${getPlatformColor(account.platform)} flex items-center justify-center text-white text-sm`}>
                        {getPlatformIcon(account.platform)}
                      </div>
                      <div>
                        <div className="font-medium capitalize">{account.platform}</div>
                        <div className="text-sm text-muted-foreground">
                          @{account.account_name}
                        </div>
                      </div>
                    </div>
                    <Badge variant={account.is_active ? "default" : "secondary"}>
                      {account.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  No social accounts connected. <a href="/dashboard/social" className="text-primary hover:underline">Connect accounts</a> to post clips.
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Caption */}
          <div className="space-y-2">
            <Label htmlFor="caption">Caption (Optional)</Label>
            <Textarea
              id="caption"
              placeholder="Add a caption for your post..."
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              className="min-h-[80px]"
            />
            <div className="text-xs text-muted-foreground">
              {caption.length}/500 characters
            </div>
          </div>

          {/* Scheduling Options */}
          <div className="space-y-4">
            <Label>Posting Schedule</Label>
            
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="immediate"
                  checked={isImmediate}
                  onCheckedChange={(checked) => setIsImmediate(checked as boolean)}
                />
                <Label htmlFor="immediate" className="flex items-center gap-2">
                  <Send className="w-4 h-4" />
                  Post immediately
                </Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="scheduled"
                  checked={!isImmediate}
                  onCheckedChange={(checked) => setIsImmediate(!checked)}
                />
                <Label htmlFor="scheduled" className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Schedule for later
                </Label>
              </div>
            </div>

            {!isImmediate && (
              <div className="space-y-2">
                <Label htmlFor="scheduledAt">Schedule Date & Time</Label>
                <Input
                  id="scheduledAt"
                  type="datetime-local"
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  min={new Date().toISOString().slice(0, 16)}
                />
                {scheduledAt && (
                  <div className="text-sm text-muted-foreground">
                    Scheduled for: {formatDateTime(scheduledAt)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Summary */}
          {selectedAccounts.length > 0 && (
            <div className="p-4 rounded-lg border bg-muted/20">
              <div className="flex items-center gap-2 mb-2">
                <Users className="w-4 h-4" />
                <span className="font-medium">Post Summary</span>
              </div>
              <div className="text-sm text-muted-foreground space-y-1">
                <div>• Posting to {selectedAccounts.length} account(s)</div>
                <div>• {isImmediate ? 'Immediate posting' : `Scheduled for ${scheduledAt ? formatDateTime(scheduledAt) : 'later'}`}</div>
                {caption && <div>• Caption: {caption.substring(0, 50)}{caption.length > 50 ? '...' : ''}</div>}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={selectedAccounts.length === 0 || schedulePost.isPending}
            >
              {schedulePost.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {isImmediate ? 'Posting...' : 'Scheduling...'}
                </>
              ) : (
                <>
                  {isImmediate ? (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Post Now
                    </>
                  ) : (
                    <>
                      <Calendar className="w-4 h-4 mr-2" />
                      Schedule Post
                    </>
                  )}
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default PostSchedulerModal;
