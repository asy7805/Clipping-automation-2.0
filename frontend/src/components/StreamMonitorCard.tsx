import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Eye, Pause, Play, Settings, Square, Users, Loader2, Wifi, Brain, Cloud, AlertTriangle, Cpu, HardDrive } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useMonitorStats } from "@/hooks/useMonitorStats";
import { useMonitorHealth } from "@/hooks/useMonitorHealth";
import { getChannelAvatarProps } from "@/lib/avatarUtils";
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

  // Fetch real-time stats and health for this monitor
  const { data: stats } = useMonitorStats(stream.channel, isLive);
  const { data: health } = useMonitorHealth(stream.channel, isLive);

  // Use real stats if available, otherwise use stream defaults
  const displayClips = stats?.clips_captured ?? stream.clips;
  const displaySegments = stats?.segments_analyzed ?? stream.segments;
  const displayLastClip = stats?.last_clip_time ?? stream.lastClip;
  
  // Get real Twitch data from health check
  const viewerCount = health?.viewer_count ?? stream.viewers;
  const streamTitle = health?.stream_title ?? stream.title;
  const gameName = health?.game_name ?? stream.category;
  const isTwitchLive = health?.is_live ?? isLive;
  const hasWarnings = health?.warnings && health.warnings.length > 0;
  
  // Get avatar props
  const { gradient, initials } = getChannelAvatarProps(stream.channel);

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
      
      // If monitor not found, it's already stopped - treat as success
      if (err.message?.includes('Not Found') || err.message?.includes('not found')) {
        console.log('Monitor already stopped, refreshing data...');
        // Refresh the monitors list
        queryClient.invalidateQueries({ queryKey: ['streams'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
        setShowStopDialog(false);
        return;
      }
      
      setError(err.message || 'Failed to stop monitor');
    } finally {
      setIsStopping(false);
    }
  };

  return (
    <Card className="p-5 md:p-6 glass-strong border-white/10 hover:border-primary/30 hover:shadow-2xl hover:shadow-primary/20 transition-all duration-300 group rounded-2xl shadow-lg shadow-primary/5">
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="relative flex-shrink-0">
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
            
            <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-white font-bold text-lg ring-2 ring-white/10`}>
              {initials}
            </div>
            
            {/* Animated Live Indicator */}
            {isTwitchLive && (
              <>
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-success rounded-full border-2 border-card animate-pulse" />
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-success rounded-full animate-ping" />
              </>
            )}
            {!isTwitchLive && isLive && (
              <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-destructive rounded-full border-2 border-card" />
            )}
          </div>
        <div className="flex-1 min-w-0 mr-3">
          <h3 className="font-bold text-foreground text-base md:text-lg truncate mb-1">{stream.channel}</h3>
          <p className="text-xs text-muted-foreground truncate max-w-[200px] mb-2">{streamTitle || stream.title}</p>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Users className="w-3.5 h-3.5" />
              <span className="font-medium">{viewerCount.toLocaleString()}</span>
            </div>
            {gameName && (
              <span className="text-xs truncate max-w-[120px]">• {gameName}</span>
            )}
          </div>
        </div>
        </div>
        
        {/* Live/Offline Status Badge */}
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          {isTwitchLive ? (
            <Badge className="border relative bg-success/10 text-success border-success/20 shadow-[0_0_15px_rgba(16,185,129,0.5)]">
              <span className="relative z-10">🔴 LIVE</span>
              <span className="absolute inset-0 bg-success/20 blur-sm rounded-full" />
            </Badge>
          ) : (
            <Badge className="border relative bg-muted text-muted-foreground border-border">
              Offline
            </Badge>
          )}
          {hasWarnings && (
            <Badge 
              variant="destructive" 
              className="text-xs cursor-help whitespace-nowrap" 
              title={health?.warnings.join(', ')}
            >
              <AlertTriangle className="w-3 h-3 mr-1" />
              {health?.warnings.length} issue{health?.warnings.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {/* Stream Info Section */}
        {health && (isTwitchLive || health.stream_title) && (
          <div className="p-3 bg-muted/20 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1.5 font-medium">Stream Info</p>
            {health.stream_title && (
              <p className="text-sm font-medium text-foreground line-clamp-2 mb-1.5 break-words">
                {health.stream_title}
              </p>
            )}
            <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
              {health.game_name && (
                <Badge variant="outline" className="text-xs flex-shrink-0">{health.game_name}</Badge>
              )}
              <span className="flex-shrink-0">•</span>
              <span className="flex-shrink-0">Uptime: {health.uptime}</span>
            </div>
          </div>
        )}

        {/* Health Indicators */}
        {health && (
          <div>
            <p className="text-xs text-muted-foreground mb-2 font-medium">System Health</p>
            <div className="grid grid-cols-3 gap-2">
              <div className={cn(
                "flex flex-col items-center gap-1 px-2 py-2 rounded-md text-xs font-medium",
                health.process_alive ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"
              )}>
                <Brain className="w-4 h-4" />
                <span>AI</span>
              </div>
              <div className={cn(
                "flex flex-col items-center gap-1 px-2 py-2 rounded-md text-xs font-medium",
                isTwitchLive ? "bg-success/10 text-success" : "bg-muted/50 text-muted-foreground"
              )}>
                <Wifi className="w-4 h-4" />
                <span>Stream</span>
              </div>
              <div className="flex flex-col items-center gap-1 px-2 py-2 rounded-md text-xs font-medium bg-success/10 text-success">
                <Cloud className="w-4 h-4" />
                <span>Upload</span>
              </div>
            </div>
          </div>
        )}

        {/* System Metrics */}
        {health && health.process_alive && (
          <div>
            <p className="text-xs text-muted-foreground mb-2 font-medium">Performance</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center justify-between px-3 py-2 bg-muted/30 rounded-md">
                <div className="flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-primary" />
                  <span>CPU</span>
                </div>
                <span className="font-mono font-bold">{health.cpu_percent}%</span>
              </div>
              <div className="flex items-center justify-between px-3 py-2 bg-muted/30 rounded-md">
                <div className="flex items-center gap-1.5">
                  <HardDrive className="w-3.5 h-3.5 text-primary" />
                  <span>RAM</span>
                </div>
                <span className="font-mono font-bold">{health.memory_mb.toFixed(0)} MB</span>
              </div>
            </div>
          </div>
        )}

        {/* Clip Stats */}
        <div>
          <p className="text-xs text-muted-foreground mb-2 font-medium">Activity</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <span className="text-base">📊</span>
              <span>{displaySegments} segments</span>
            </div>
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <span className="text-base">📹</span>
              <span>{displayClips} clips</span>
            </div>
            <div className="col-span-2 text-xs text-muted-foreground">
              Last clip: {displayLastClip || 'analyzing...'}
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-muted-foreground font-medium">
              Buffer: {stream.bufferCount.current}/{stream.bufferCount.total}
            </span>
            <span className="text-primary font-bold">{Math.round(stream.bufferProgress * 100)}%</span>
          </div>
          <div className="w-full bg-muted/30 rounded-full h-2 overflow-hidden">
            <div 
              className="h-full rounded-full bg-gradient-to-r from-primary via-pink-500 to-primary bg-[length:200%_100%] animate-[shimmer_3s_linear_infinite] transition-all duration-500"
              style={{ width: `${stream.bufferProgress * 100}%` }}
            />
          </div>
        </div>

        <div className="flex items-center gap-2 pt-3 border-t border-white/10">
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
