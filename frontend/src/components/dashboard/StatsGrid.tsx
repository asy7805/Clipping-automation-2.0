import { Activity, Film, HardDrive, Star } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useDashboardStats } from "@/hooks/useStreamData";
import { useEffect, useState } from "react";

export const StatsGrid = () => {
  const { data: stats, isLoading } = useDashboardStats();
  const [displayStats, setDisplayStats] = useState({
    clipsToday: 127,
    avgScore: 0.54,
    storageUsed: 3.8
  });

  // Smooth transition for stats
  useEffect(() => {
    if (stats) {
      // Animate number changes
      const animateValue = (
        start: number, 
        end: number, 
        duration: number, 
        callback: (value: number) => void
      ) => {
        const startTime = performance.now();
        const animate = (currentTime: number) => {
          const elapsed = currentTime - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const value = start + (end - start) * progress;
          callback(value);
          if (progress < 1) {
            requestAnimationFrame(animate);
          }
        };
        requestAnimationFrame(animate);
      };

      animateValue(displayStats.clipsToday, stats.clipsToday, 800, (value) => {
        setDisplayStats(prev => ({ ...prev, clipsToday: Math.round(value) }));
      });

      animateValue(displayStats.avgScore, stats.avgScore, 800, (value) => {
        setDisplayStats(prev => ({ ...prev, avgScore: value }));
      });

      animateValue(displayStats.storageUsed, stats.storageUsed, 800, (value) => {
        setDisplayStats(prev => ({ ...prev, storageUsed: value }));
      });
    }
  }, [stats]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card className="p-6 glass-strong border-white/10 hover:border-primary/30 transition-all group">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Active Monitors</p>
            <p className="text-4xl font-bold text-foreground count-up glow-text transition-all duration-500">
              {stats?.activeMonitors ?? 3}
            </p>
            <p className="text-xs text-success mt-2 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-success pulse-dot" />
              +2 today
            </p>
          </div>
          <div className="w-14 h-14 rounded-xl bg-success/10 flex items-center justify-center ring-2 ring-success/20 group-hover:scale-110 transition-transform">
            <Activity className="w-7 h-7 text-success" />
          </div>
        </div>
      </Card>

      <Card className="p-6 glass-strong border-white/10 hover:border-primary/30 transition-all group">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Clips Today</p>
            <p className="text-4xl font-bold text-foreground count-up glow-text transition-all duration-500">
              {displayStats.clipsToday}
            </p>
            <p className="text-xs text-success mt-2">↑ {stats?.clipsTrend ?? 23}% vs yesterday</p>
          </div>
          <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center ring-2 ring-primary/20 group-hover:scale-110 transition-transform">
            <Film className="w-7 h-7 text-primary" />
          </div>
        </div>
      </Card>

      <Card className="p-6 glass-strong border-white/10 hover:border-primary/30 transition-all group">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Storage Used</p>
            <p className="text-4xl font-bold text-foreground glow-text transition-all duration-500">
              {displayStats.storageUsed.toFixed(1)}
            </p>
            <p className="text-xs text-muted-foreground">GB</p>
            <div className="mt-3 w-full bg-muted/30 rounded-full h-2.5 overflow-hidden">
              <div 
                className="h-full rounded-full bg-gradient-to-r from-primary via-pink-500 to-primary bg-[length:200%_100%] animate-[shimmer_3s_linear_infinite] transition-all duration-1000"
                style={{ width: `${((stats?.storageUsed ?? 3.8) / (stats?.storageTotal ?? 10)) * 100}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1.5">of {stats?.storageTotal ?? 10} GB</p>
          </div>
          <div className="w-14 h-14 rounded-xl bg-info/10 flex items-center justify-center ring-2 ring-info/20 group-hover:scale-110 transition-transform">
            <HardDrive className="w-7 h-7 text-info" />
          </div>
        </div>
      </Card>

      <Card className="p-6 glass-strong border-white/10 hover:border-primary/30 transition-all group">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Avg AI Score</p>
            <p className="text-4xl font-bold text-foreground glow-text transition-all duration-500">
              {displayStats.avgScore.toFixed(2)}
            </p>
            <div className="flex gap-0.5 mt-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star
                  key={star}
                  className={`w-3.5 h-3.5 transition-all duration-300 ${
                    star <= 3 ? 'fill-score-blue text-score-blue' : 'text-muted'
                  }`}
                />
              ))}
            </div>
            <p className="text-xs text-success mt-2">↑ {stats?.scoreTrend.toFixed(2) ?? '0.03'}</p>
          </div>
          <div className="w-14 h-14 rounded-xl bg-warning/10 flex items-center justify-center ring-2 ring-warning/20 group-hover:scale-110 transition-transform">
            <Star className="w-7 h-7 text-warning" />
          </div>
        </div>
      </Card>
    </div>
  );
};
