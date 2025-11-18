import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Database, HardDrive, Settings2, Zap, Bell, Brain } from "lucide-react";
import { useDashboardStats } from "@/hooks/useStreamData";
import { useClips } from "@/hooks/useClips";
import { useMemo } from "react";

const Settings = () => {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: clipsData } = useClips({ limit: 1000 });

  const { storageUsedGB, storageQuotaGB, totalClips, avgClipSizeMB, storagePercent } = useMemo(() => {
    const used = stats?.storageUsed ?? 0;
    const quota = stats?.storageTotal ?? 10;
    const clips = clipsData?.clips ?? [];
    const totalSizeBytes = clips.reduce((sum, clip) => sum + (clip.file_size || 0), 0);
    const averageMB = clips.length ? (totalSizeBytes / clips.length) / (1024 * 1024) : 0;

    return {
      storageUsedGB: Math.round(used * 100) / 100,
      storageQuotaGB: quota,
      totalClips: clips.length,
      avgClipSizeMB: Math.round(averageMB),
      storagePercent: Math.min(100, quota ? (used / quota) * 100 : 0)
    };
  }, [stats, clipsData]);

  const isLoading = statsLoading;

  return (
    <div className="container mx-auto px-6 py-8 max-w-5xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">⚙️ Settings</h1>
        <p className="text-muted-foreground">Manage your AscensionClips configuration</p>
      </div>

      {/* Current Configuration - Read Only */}
      <Card className="p-6 bg-card border-border">
        <div className="flex items-center gap-3 mb-6">
          <Settings2 className="w-6 h-6 text-primary" />
          <h2 className="text-xl font-semibold">Current Configuration</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 bg-muted/30 rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-primary" />
              <h3 className="font-semibold">Stream Capture</h3>
            </div>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>✓ 30-second segments</p>
              <p>✓ 720p60 quality</p>
              <p>✓ Auto-restart enabled</p>
            </div>
          </div>

          <div className="p-4 bg-muted/30 rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-primary" />
              <h3 className="font-semibold">AI Processing</h3>
            </div>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>✓ Audio analysis (librosa)</p>
              <p>✓ Speech-to-text (Whisper)</p>
              <p>✓ Emotion detection (DistilBERT)</p>
            </div>
          </div>

          <div className="p-4 bg-muted/30 rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-2">
              <HardDrive className="w-4 h-4 text-primary" />
              <h3 className="font-semibold">Clip Strategy</h3>
            </div>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>✓ Collect 5 segments</p>
              <p>✓ Select top 3 clips</p>
              <p>✓ Merge interesting moments</p>
            </div>
          </div>

          <div className="p-4 bg-muted/30 rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-primary" />
              <h3 className="font-semibold">Storage</h3>
            </div>
            <div className="space-y-1 text-sm text-muted-foreground">
              <p>✓ Supabase Storage</p>
              <p>✓ MP4 format (H.264)</p>
              <p>✓ Public URLs enabled</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Storage Management - Real Data */}
      <Card className="p-6 bg-card border-border">
        <div className="flex items-center gap-3 mb-6">
          <HardDrive className="w-6 h-6 text-primary" />
          <h2 className="text-xl font-semibold">Storage Management</h2>
        </div>
        
        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-3">
              <Label className="text-base">Current Usage</Label>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold">
                  {isLoading ? "..." : storageUsedGB.toFixed(2)} GB
                </span>
                <span className="text-muted-foreground">/ {storageQuotaGB} GB</span>
              </div>
            </div>
            <div className="w-full bg-muted rounded-full h-4 relative overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${
                  storagePercent > 80 
                    ? 'bg-gradient-to-r from-destructive to-red-600' 
                    : storagePercent > 60
                    ? 'bg-gradient-to-r from-warning to-yellow-500'
                    : 'bg-gradient-to-r from-primary to-pink-500'
                }`}
                style={{ width: `${storagePercent}%` }} 
              />
            </div>
            <div className="flex items-center justify-between mt-2 text-sm text-muted-foreground">
              <span>{storagePercent.toFixed(1)}% used</span>
              <span>{(storageQuotaGB - storageUsedGB).toFixed(2)} GB remaining</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-muted/30 rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">Total Clips</p>
              <p className="text-2xl font-bold">{totalClips}</p>
            </div>
            <div className="p-3 bg-muted/30 rounded-lg">
              <p className="text-xs text-muted-foreground mb-1">Avg Clip Size</p>
              <p className="text-2xl font-bold">{avgClipSizeMB} MB</p>
            </div>
          </div>

          <div className="p-4 bg-muted/20 rounded-lg border border-border">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <Database className="w-4 h-4" />
              Supabase Free Tier
            </h3>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>• {storageQuotaGB} GB storage included</p>
              <p>• Unlimited bandwidth</p>
              <p>• Files stored in <code className="text-xs bg-muted px-1 py-0.5 rounded">raw/</code> bucket</p>
            </div>
          </div>

          {storagePercent > 80 && (
            <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
              <p className="text-sm font-semibold text-destructive mb-1">
                ⚠️ Storage Warning
              </p>
              <p className="text-sm text-muted-foreground">
                You're using over 80% of your storage quota. Consider cleaning up old clips.
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Coming Soon */}
      <Card className="p-6 bg-card border-border border-dashed">
        <div className="flex items-center gap-3 mb-4">
          <Bell className="w-6 h-6 text-muted-foreground" />
          <h2 className="text-xl font-semibold text-muted-foreground">🚧 Coming Soon</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-muted/20 rounded-lg">
            <h3 className="font-semibold mb-2">AI Tuning Controls</h3>
            <p className="text-sm text-muted-foreground">
              Adjust detection thresholds, weights for audio/emotion/keywords
            </p>
          </div>

          <div className="p-4 bg-muted/20 rounded-lg">
            <h3 className="font-semibold mb-2">Webhook Notifications</h3>
            <p className="text-sm text-muted-foreground">
              Send alerts to Discord/Slack when high-score clips are captured
            </p>
          </div>

          <div className="p-4 bg-muted/20 rounded-lg">
            <h3 className="font-semibold mb-2">Auto Cleanup</h3>
            <p className="text-sm text-muted-foreground">
              Automatically delete old clips after X days to save storage
            </p>
          </div>

          <div className="p-4 bg-muted/20 rounded-lg">
            <h3 className="font-semibold mb-2">Quality Presets</h3>
            <p className="text-sm text-muted-foreground">
              Choose between 1080p60, 720p60, or 480p for faster processing
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Settings;
