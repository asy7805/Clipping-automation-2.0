import { Activity, Film, HardDrive, Star } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useDashboardStats } from "@/hooks/useStreamData";
import { useEffect, useState } from "react";

export const StatsGrid = () => {
  const { data: stats, isLoading } = useDashboardStats();
  const [displayStats, setDisplayStats] = useState({
    clipsToday: 127,
    avgScore: 0.54,
    storageUsed: 3.8,
    totalClips: 0
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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
      <Card className="p-4 md:p-5 glass-strong border-white/10 hover:border-primary/30 transition-all group min-h-[160px] flex flex-col justify-between rounded-2xl shadow-lg shadow-primary/5">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-xs md:text-sm text-muted-foreground mb-2 font-medium">Active Monitors</p>
            <p className="text-3xl md:text-4xl font-bold text-foreground count-up glow-text transition-all duration-500 mb-2">
              {stats?.activeMonitors ?? 3}
            </p>
            <p className="text-xs text-success flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-success pulse-dot" />
              +2 today
            </p>
          </div>
          <div className="w-12 h-12 md:w-14 md:h-14 rounded-xl bg-success/10 flex items-center justify-center ring-2 ring-success/20 group-hover:scale-110 transition-transform flex-shrink-0 ml-3">
            <Activity className="w-6 h-6 md:w-7 md:h-7 text-success" />
          </div>
        </div>
      </Card>

      <Card className="p-4 md:p-5 glass-strong border-white/10 hover:border-primary/30 transition-all group min-h-[160px] flex flex-col justify-between rounded-2xl shadow-lg shadow-primary/5">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-xs md:text-sm text-muted-foreground mb-2 font-medium">Clips Today</p>
            <p className="text-3xl md:text-4xl font-bold text-foreground count-up glow-text transition-all duration-500 mb-2">
              {displayStats.clipsToday}
            </p>
            <p className="text-xs text-success">↑ {stats?.clipsTrend ?? 23}% vs yesterday</p>
          </div>
          <div className="w-12 h-12 md:w-14 md:h-14 rounded-xl bg-primary/10 flex items-center justify-center ring-2 ring-primary/20 group-hover:scale-110 transition-transform flex-shrink-0 ml-3">
            <Film className="w-6 h-6 md:w-7 md:h-7 text-primary" />
          </div>
        </div>
      </Card>

      <Card className="p-4 md:p-5 glass-strong border-white/10 hover:border-primary/30 transition-all group min-h-[160px] flex flex-col justify-between rounded-2xl shadow-lg shadow-primary/5">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-xs md:text-sm text-muted-foreground mb-2 font-medium">Storage Used</p>
            <p className="text-3xl md:text-4xl font-bold text-foreground glow-text transition-all duration-500 mb-2">
              {displayStats.storageUsed.toFixed(1)}
              <span className="text-lg text-muted-foreground ml-1">GB</span>
            </p>
            <div className="mt-2 w-full bg-muted/30 rounded-full h-2 overflow-hidden">
              <div 
                className="h-full rounded-full bg-gradient-to-r from-primary via-pink-500 to-primary bg-[length:200%_100%] animate-[shimmer_3s_linear_infinite] transition-all duration-1000"
                style={{ width: `${((stats?.storageUsed ?? 3.8) / (stats?.storageTotal ?? 10)) * 100}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1.5">of {stats?.storageTotal ?? 10} GB</p>
          </div>
          <div className="w-12 h-12 md:w-14 md:h-14 rounded-xl bg-info/10 flex items-center justify-center ring-2 ring-info/20 group-hover:scale-110 transition-transform flex-shrink-0 ml-3">
            <HardDrive className="w-6 h-6 md:w-7 md:h-7 text-info" />
          </div>
        </div>
      </Card>

      <Card className="p-4 md:p-5 glass-strong border-white/10 hover:border-primary/30 transition-all group min-h-[160px] flex flex-col justify-between rounded-2xl shadow-lg shadow-primary/5">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-xs md:text-sm text-muted-foreground mb-2 font-medium">Total Segments</p>
            <p className="text-3xl md:text-4xl font-bold text-foreground glow-text transition-all duration-500 mb-2">
              {displayStats.totalClips || stats?.clipsToday || 0}
            </p>
            <div className="flex items-center gap-2 mt-2">
              <div className="flex gap-0.5">
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star
                    key={star}
                    className={`w-3 h-3 md:w-3.5 md:h-3.5 transition-all duration-300 ${
                      star <= 3 ? 'fill-score-blue text-score-blue' : 'text-muted'
                    }`}
                  />
                ))}
              </div>
              <p className="text-xs text-success">↑ {stats?.scoreTrend.toFixed(2) ?? '0.03'}</p>
            </div>
          </div>
          <div className="w-12 h-12 md:w-14 md:h-14 rounded-xl bg-warning/10 flex items-center justify-center ring-2 ring-warning/20 group-hover:scale-110 transition-transform flex-shrink-0 ml-3">
            <Star className="w-6 h-6 md:w-7 md:h-7 text-warning" />
          </div>
        </div>
      </Card>
    </div>
  );
};
