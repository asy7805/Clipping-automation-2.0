import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, ExternalLink } from "lucide-react";
import { apiClient } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";

interface AddMonitorModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddMonitorModal({ open, onOpenChange }: AddMonitorModalProps) {
  const [twitchUrl, setTwitchUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const extractChannelName = (url: string): string => {
    // Extract channel name from URL for preview
    const cleaned = url.trim().toLowerCase()
      .replace(/^https?:\/\//i, '')
      .replace(/^www\./i, '')
      .replace(/^twitch\.tv\//i, '')
      .split('?')[0]
      .split('/')[0]
      .trim();
    return cleaned;
  };

  const channelPreview = twitchUrl ? extractChannelName(twitchUrl) : null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await apiClient.startMonitor(twitchUrl);
      
      // Invalidate queries to refresh the monitors list
      queryClient.invalidateQueries({ queryKey: ['streams'] }); // This fetches monitors now
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      
      // Close modal and reset
      onOpenChange(false);
      setTwitchUrl("");
      
      // Show success message
      console.log("Monitor started:", response);
    } catch (err: any) {
      setError(err.message || "Failed to start monitor. Please check the URL and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setTwitchUrl("");
      setError(null);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            🔴 Add Live Monitor
          </DialogTitle>
          <DialogDescription>
            Enter a Twitch stream URL to start AI-powered clip detection
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="twitch-url">Twitch Stream URL</Label>
              <Input
                id="twitch-url"
                placeholder="https://twitch.tv/channelname"
                value={twitchUrl}
                onChange={(e) => setTwitchUrl(e.target.value)}
                disabled={isLoading}
                autoFocus
              />
              {channelPreview && (
                <p className="text-sm text-muted-foreground">
                  Channel: <span className="font-medium text-foreground">{channelPreview}</span>
                </p>
              )}
            </div>

            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}

            <div className="p-4 bg-muted/50 rounded-md space-y-2">
              <h4 className="font-medium text-sm">✨ What happens next:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>AI starts monitoring the stream in real-time</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Captures 30-second segments automatically</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Best moments saved to your dashboard</span>
                </li>
              </ul>
            </div>

            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <ExternalLink className="w-4 h-4" />
              <span>
                Example: <code className="text-xs">twitch.tv/shroud</code>
              </span>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!twitchUrl.trim() || isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Starting Monitor...
                </>
              ) : (
                "Start Monitoring"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

