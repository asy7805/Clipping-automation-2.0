import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Eye, Pause, Play, Settings, Square, Users, Loader2 } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useMonitorStats } from "@/hooks/useMonitorStats";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface StreamMonitorCardProps {
  stream: {
    id: string;
    channel: string;
    avatar: string;
    title: string;
    category: string;
    viewers: number;
    status: "analyzing" | "processing" | "paused";
    runtime: string;
    segments: number;
    clips: number;
    lastClip: string;
    bufferProgress: number;
    bufferCount: { current: number; total: number };
  };
}

export const StreamMonitorCard = ({ stream }: StreamMonitorCardProps) => {
  const [isStopping, setIsStopping] = useState(false);
  const [showStopDialog, setShowStopDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const statusColors = {
    analyzing: "bg-success/10 text-success border-success/20",
    processing: "bg-warning/10 text-warning border-warning/20",
    paused: "bg-muted text-muted-foreground border-border"
  };

  const isLive = stream.status !== "paused";

  // Fetch real-time stats for this monitor
  const { data: stats } = useMonitorStats(stream.channel, isLive);

  // Use real stats if available, otherwise use stream defaults
  const displayClips = stats?.clips_captured ?? stream.clips;
  const displaySegments = stats?.segments_analyzed ?? stream.segments;
  const displayLastClip = stats?.last_clip_time ?? stream.lastClip;

  // Handle View button - navigate to clips filtered by channel
  const handleView = () => {
    navigate(`/dashboard/clips?channel=${stream.channel}`);
  };

  // Handle Stop button - terminate monitoring
  const handleStop = async () => {
    setIsStopping(true);
    setError(null);

    try {
      await apiClient.stopMonitor(stream.channel);
      
      // Refresh the monitors list
      queryClient.invalidateQueries({ queryKey: ['streams'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      
      // Close dialog
      setShowStopDialog(false);
    } catch (err: any) {
      console.error('Failed to stop monitor:', err);
      setError(err.message || 'Failed to stop monitor');
    } finally {
      setIsStopping(false);
    }
  };

  return (
    <Card className="p-6 glass-strong border-white/10 hover:border-primary/30 hover:shadow-2xl hover:shadow-primary/20 transition-all duration-300 group">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            {/* Circular Progress Ring */}
            <svg className="absolute -inset-1 w-[56px] h-[56px] -rotate-90">
              {/* Background circle */}
              <circle
                cx="28"
                cy="28"
                r="26"
                stroke="hsl(var(--muted))"
                strokeWidth="2"
                fill="none"
                opacity="0.2"
              />
              {/* Progress circle */}
              <circle
                cx="28"
                cy="28"
                r="26"
                stroke="url(#gradient)"
                strokeWidth="2"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 26}`}
                strokeDashoffset={`${2 * Math.PI * 26 * (1 - stream.bufferProgress)}`}
                strokeLinecap="round"
                className="transition-all duration-500"
              />
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="hsl(var(--primary))" />
                  <stop offset="100%" stopColor="hsl(var(--accent))" />
                </linearGradient>
              </defs>
            </svg>
            
            <Avatar className="w-12 h-12 ring-2 ring-white/10">
              <AvatarImage src={stream.avatar} alt={stream.channel} />
              <AvatarFallback>{stream.channel[0].toUpperCase()}</AvatarFallback>
            </Avatar>
            
            {/* Animated Live Indicator */}
            {isLive && (
              <>
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-success rounded-full border-2 border-card animate-pulse" />
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-success rounded-full animate-ping" />
              </>
            )}
          </div>
          <div>
            <h3 className="font-bold text-foreground text-lg">{stream.channel}</h3>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Users className="w-3.5 h-3.5" />
              <span className="font-medium">{stream.viewers}</span>
            </div>
          </div>
        </div>
        
        {/* Glowing Status Badge */}
        <Badge className={cn(
          "border relative",
          statusColors[stream.status],
          stream.status === "analyzing" && "shadow-[0_0_15px_rgba(16,185,129,0.5)]",
          stream.status === "processing" && "shadow-[0_0_15px_rgba(245,158,11,0.5)]"
        )}>
          {stream.status === "analyzing" && (
            <>
              <span className="relative z-10">Analyzing</span>
              <span className="absolute inset-0 bg-success/20 blur-sm rounded-full" />
            </>
          )}
          {stream.status === "processing" && (
            <>
              <span className="relative z-10">Processing</span>
              <span className="absolute inset-0 bg-warning/20 blur-sm rounded-full" />
            </>
          )}
          {stream.status === "paused" && "Offline"}
        </Badge>
      </div>

      <div className="space-y-4">
        <div>
          <p className="text-sm text-foreground line-clamp-2 mb-2 leading-relaxed">{stream.title}</p>
          <Badge variant="outline" className="text-xs text-info border-info/30 bg-info/10">
            {stream.category}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-muted-foreground flex items-center gap-1">
            <span className="text-base">⏱️</span> {stream.runtime}
          </div>
          <div className="text-muted-foreground flex items-center gap-1">
            <span className="text-base">📊</span> {displaySegments} segments
          </div>
          <div className="text-muted-foreground flex items-center gap-1">
            <span className="text-base">📹</span> {displayClips} clips
          </div>
          <div className="text-muted-foreground text-xs self-center">
            Last: {displayLastClip || 'analyzing...'}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-muted-foreground font-medium">
              Buffer: {stream.bufferCount.current}/{stream.bufferCount.total}
            </span>
            <span className="text-primary font-bold">{Math.round(stream.bufferProgress * 100)}%</span>
          </div>
          <div className="w-full bg-muted/30 rounded-full h-2.5 overflow-hidden">
            <div 
              className="h-full rounded-full bg-gradient-to-r from-primary via-pink-500 to-primary bg-[length:200%_100%] animate-[shimmer_3s_linear_infinite] transition-all duration-500"
              style={{ width: `${stream.bufferProgress * 100}%` }}
            />
          </div>
        </div>

        <div className="flex items-center gap-2 pt-2 border-t border-white/10">
          <Button 
            size="sm" 
            variant="outline" 
            className="flex-1 border-white/10 hover:bg-white/5 hover:border-primary/30"
            onClick={handleView}
            title="View clips"
          >
            <Eye className="w-4 h-4" />
          </Button>
          <Button 
            size="sm" 
            variant="outline" 
            className="flex-1 border-white/10 hover:bg-white/5 hover:border-primary/30"
            disabled
            title="Pause/Resume (coming soon)"
          >
            {stream.status === "paused" ? (
              <Play className="w-4 h-4" />
            ) : (
              <Pause className="w-4 h-4" />
            )}
          </Button>
          <Button 
            size="sm" 
            variant="outline" 
            className="flex-1 border-white/10 hover:bg-white/5 hover:border-primary/30"
            disabled
            title="Settings (coming soon)"
          >
            <Settings className="w-4 h-4" />
          </Button>
          <Button 
            size="sm" 
            variant="outline" 
            className="flex-1 border-white/10 hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30"
            onClick={() => setShowStopDialog(true)}
            disabled={isStopping}
            title="Stop monitoring"
          >
            {isStopping ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Square className="w-4 h-4" />
            )}
          </Button>
        </div>

        {error && (
          <div className="mt-2 p-2 bg-destructive/10 border border-destructive/20 rounded text-xs text-destructive">
            {error}
          </div>
        )}
      </div>

      {/* Stop Confirmation Dialog */}
      <AlertDialog open={showStopDialog} onOpenChange={setShowStopDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Stop Monitoring?</AlertDialogTitle>
            <AlertDialogDescription>
              This will stop monitoring <span className="font-semibold text-foreground">{stream.channel}</span>.
              The process will be terminated and no new clips will be captured.
              <br /><br />
              You can start monitoring again anytime from the Add Monitor button.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isStopping}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleStop}
              disabled={isStopping}
              className="bg-destructive hover:bg-destructive/90"
            >
              {isStopping ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Stopping...
                </>
              ) : (
                'Stop Monitoring'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
};
